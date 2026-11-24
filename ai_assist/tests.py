import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from botocore.exceptions import ClientError
from ai_assist.services import get_ai_suggestions, AISuggestionError


class AIAssistTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='password123')
        self.suggest_url = reverse('ai_suggest')
        cache.clear()

    def test_anonymous_user_cannot_access_ai_suggest(self):
        """Logged-out user is blocked from the AI API."""
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': 'Some long technical text for post content.'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_short_body_rejected_with_friendly_error(self):
        """Bodies shorter than 30 characters return 400 with guidance."""
        self.client.login(username='dave', password='password123')
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': 'Too short'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('at least 30 characters', data['error'])

    @override_settings(AI_MOCK_MODE=True)
    def test_mock_mode_returns_realistic_suggestions(self):
        """Mock mode returns structured, content-aware suggestions with mode='mock'."""
        self.client.login(username='dave', password='password123')
        body = (
            "Amazon Bedrock offers high performance foundation models from top AI startups "
            "and Amazon available through a single unified API. It provides security, privacy, "
            "and responsible AI capabilities."
        )
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': body}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['mode'], 'mock')

        suggestions = data['suggestions']
        self.assertGreaterEqual(len(suggestions['titles']), 3)
        self.assertGreaterEqual(len(suggestions['hashtags']), 5)
        self.assertTrue(isinstance(suggestions['summary'], str))
        self.assertGreater(len(suggestions['summary']), 10)

    @override_settings(AI_MOCK_MODE=True)
    def test_mock_mode_distinct_styles_and_stop_words_removal(self):
        """Mock suggestions produce 4 titles in distinct styles and omit tech boilerplate for non-tech text."""
        self.client.login(username='dave', password='password123')
        non_tech_body = (
            "They are very excited about our peaceful morning walk in the quiet botanical garden. "
            "Fresh flowers and trees brought a deep sense of calm and rejuvenation to the whole family."
        )
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': non_tech_body}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        suggestions = data['suggestions']
        titles = suggestions['titles']
        self.assertEqual(len(titles), 4)

        # Verify no generic tech boilerplate in non-tech post
        for t in titles:
            self.assertNotIn("Building Scalable Systems", t)
            self.assertNotIn("Best Practices", t)

        # Verify stop words are not present in hashtags
        hashtags = suggestions['hashtags']
        for stop in ['very', 'they', 'the', 'in', 'our', 'and']:
            self.assertNotIn(stop, hashtags)

        # Verify summary is author's first sentence trimmed <= 150 chars
        self.assertLessEqual(len(suggestions['summary']), 150)
        self.assertTrue(suggestions['summary'].startswith("They are very excited"))

    @override_settings(AI_MOCK_MODE=False, AWS_REGION='ap-southeast-2', BEDROCK_MODEL_ID='amazon.nova-lite-v1:0')
    @patch('boto3.client')
    def test_real_bedrock_converse_path_with_mocked_boto3(self, mock_boto3_client):
        """Verify the real Bedrock Converse API invocation and schema validation."""
        self.client.login(username='dave', password='password123')

        # Mock the Bedrock Converse response
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        mock_ai_json = {
            "titles": [
                "Deploying High Availability Django on AWS",
                "Automating Cloud Infrastructure with Terraform",
                "Production Architecture Guide"
            ],
            "hashtags": ["aws", "django", "cloud", "devops", "python"],
            "summary": "A comprehensive guide on deploying scalable Django applications on AWS."
        }

        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': json.dumps(mock_ai_json)}
                    ]
                }
            }
        }

        body = "This is a detailed technical article about deploying Django on AWS with Auto Scaling and RDS."
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': body}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['mode'], 'bedrock')
        self.assertEqual(data['model'], 'amazon.nova-lite-v1:0')
        self.assertEqual(data['region'], 'ap-southeast-2')
        self.assertEqual(data['suggestions']['titles'][0], "Deploying High Availability Django on AWS")
        self.assertEqual(data['suggestions']['hashtags'], ["aws", "django", "cloud", "devops", "python"])

        # Verify Converse API was called with the configured model
        mock_bedrock.converse.assert_called_once()
        call_kwargs = mock_bedrock.converse.call_args[1]
        self.assertEqual(call_kwargs['modelId'], 'amazon.nova-lite-v1:0')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'ap-southeast-2')

    @override_settings(AI_MOCK_MODE=False, AWS_REGION='ap-southeast-2', BEDROCK_MODEL_ID='amazon.nova-lite-v1:0')
    @patch('boto3.client')
    def test_bedrock_response_with_greeting_and_code_fences(self, mock_boto3_client):
        """Verify resilient JSON raw_decode handling greetings, markdown fences, and trailing prose."""
        self.client.login(username='dave', password='password123')

        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        messy_ai_output = (
            "Here are your suggestions for this article:\n"
            "```json\n"
            "{\n"
            '  "titles": ["Mastering Amazon Nova Lite", "Serverless Django on AWS", "Cost Optimization 101"],\n'
            '  "hashtags": ["#NovaLite", "#AWS", "#Cloud", "#Django", "#Architecture"],\n'
            '  "summary": "A deep dive into cost-effective AI integration with Amazon Nova Lite."\n'
            "}\n"
            "```\n"
            "Hope this helps with your publication workflow!"
        )

        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': messy_ai_output}
                    ]
                }
            }
        }

        body = "A technical draft analyzing cost optimization when utilizing Amazon Nova Lite foundation models."
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': body}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['mode'], 'bedrock')
        self.assertEqual(data['model'], 'amazon.nova-lite-v1:0')
        self.assertEqual(data['region'], 'ap-southeast-2')
        # Cleaned tags should have '#' removed and lowercased
        self.assertEqual(data['suggestions']['hashtags'], ["novalite", "aws", "cloud", "django", "architecture"])
        self.assertEqual(len(data['suggestions']['titles']), 3)

    @override_settings(AI_MOCK_MODE=False, AWS_REGION='ap-southeast-2')
    @patch('time.sleep', return_value=None)
    @patch('boto3.client')
    def test_bedrock_outage_graceful_degradation(self, mock_boto3_client, mock_sleep):
        """Simulate Bedrock Throttling or Outage: API returns clean 400 error, never a 500 crash."""
        self.client.login(username='dave', password='password123')

        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Simulate ClientError (e.g. AWS outage or ThrottlingException)
        mock_bedrock.converse.side_effect = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='Converse'
        )

        body = "Writing a long blog post to test error handling when AWS is unreachable."
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': body}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('ThrottlingException', data['error'])

    @override_settings(AI_MOCK_MODE=False, AWS_REGION='ap-southeast-2')
    @patch('boto3.client')
    def test_bedrock_malformed_json_returns_friendly_error(self, mock_boto3_client):
        """When AI returns non-JSON or conversational refusal, return friendly 400 without crashing."""
        self.client.login(username='dave', password='password123')

        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': "I am sorry, but I cannot fulfill this request."}
                    ]
                }
            }
        }

        body = "Testing what happens when AI output contains no JSON structure."
        response = self.client.post(
            self.suggest_url,
            data=json.dumps({'body': body}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No valid JSON object found', data['error'])

    def test_rate_limiting_enforcement(self):
        """Sending more than 5 requests in a minute returns HTTP 429."""
        self.client.login(username='dave', password='password123')
        body = {'body': 'A sufficiently long blog post content for rate limit testing.'}

        # Send 5 allowed requests
        for _ in range(5):
            res = self.client.post(self.suggest_url, data=json.dumps(body), content_type='application/json')
            self.assertEqual(res.status_code, 200)

        # 6th request triggers rate limit
        res_blocked = self.client.post(self.suggest_url, data=json.dumps(body), content_type='application/json')
        self.assertEqual(res_blocked.status_code, 429)
        self.assertIn("Rate limit exceeded", res_blocked.json()['error'])

    def test_ensure_tag_endpoint(self):
        """Dynamic tag endpoint creates new tags and returns existing ones."""
        self.client.login(username='dave', password='password123')
        ensure_url = reverse('ai_ensure_tag')

        # Create new tag
        res1 = self.client.post(
            ensure_url,
            data=json.dumps({'tag': '#Serverless'}),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['name'], 'serverless')
        self.assertTrue(data1['created'])

        # Query existing tag
        res2 = self.client.post(
            ensure_url,
            data=json.dumps({'tag': 'serverless'}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2['success'])
        self.assertEqual(data2['id'], data1['id'])
        self.assertFalse(data2['created'])
