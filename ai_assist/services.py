import json
import re
import string
import logging
from typing import Dict, Any, List
from django.conf import settings
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
import boto3

logger = logging.getLogger(__name__)


class AISuggestionError(Exception):
    """Custom exception raised when suggestion generation fails."""
    pass


def _extract_keywords(text: str, max_words: int = 6) -> List[str]:
    """Helper to extract clean alphanumeric keywords from post body for mock suggestions."""
    # Remove punctuation and lowercase
    cleaned = text.translate(str.maketrans('', '', string.punctuation)).lower()
    stop_words = {
        'the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'that', 'you', 'for', 'with', 
        'on', 'as', 'are', 'this', 'was', 'at', 'by', 'an', 'be', 'from', 'or', 'about'
    }
    words = [w for w in cleaned.split() if len(w) > 3 and w not in stop_words]
    # Deduplicate while preserving order
    seen = set()
    keywords = []
    for w in words:
        if w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= max_words:
            break
    return keywords or ['cloud', 'development', 'guide']


def _generate_mock_suggestions(body_text: str) -> Dict[str, Any]:
    """
    Generate realistic, content-aware mock suggestions without calling AWS.
    Produces the exact same JSON schema as the Amazon Bedrock path.
    """
    keywords = _extract_keywords(body_text)
    primary_topic = keywords[0].capitalize() if keywords else "Modern Architecture"
    secondary_topic = keywords[1].capitalize() if len(keywords) > 1 else "Best Practices"

    # 3 to 4 realistic titles
    titles = [
        f"{primary_topic}: A Practical Guide and Best Practices",
        f"Mastering {primary_topic} and {secondary_topic} from Scratch",
        f"Everything You Need to Know About {primary_topic}",
        f"Deep Dive: Building Scalable Systems with {primary_topic}",
    ]

    # 5 to 7 hashtags (stored lowercase without '#')
    base_tags = [k.lower() for k in keywords]
    fallback_tags = ['aws', 'cloud', 'django', 'python', 'architecture', 'webdev']
    tags_pool = []
    for t in base_tags + fallback_tags:
        if t not in tags_pool and len(t) <= 20:
            tags_pool.append(t)
        if len(tags_pool) >= 6:
            break

    # Summary: First sentence or derived summary
    sentences = re.split(r'[.!?]+', body_text.strip())
    first_sentence = sentences[0].strip() if sentences and len(sentences[0].strip()) > 20 else ""
    if first_sentence:
        summary = first_sentence if len(first_sentence) <= 250 else f"{first_sentence[:247]}..."
    else:
        summary = f"An in-depth overview exploring {primary_topic.lower()} principles and practical implementation steps."

    return {
        "titles": titles,
        "hashtags": tags_pool,
        "summary": summary,
    }


def _invoke_bedrock(body_text: str) -> Dict[str, Any]:
    """
    Invoke Amazon Bedrock Runtime via the unified Converse API.
    Expects strict JSON containing titles, hashtags, and summary.
    """
    system_prompt = (
        "You are an expert editorial assistant for a technical software blog. "
        "Analyze the provided blog post draft and return creative titles, relevant hashtags, "
        "and a concise summary. "
        "You must respond ONLY with a valid JSON object matching this schema: "
        '{"titles": ["Title 1", "Title 2", "Title 3"], '
        '"hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"], '
        '"summary": "One clear sentence summarizing the post."} '
        "Do not include any commentary, explanations, or markdown fences outside the JSON."
    )

    user_message = f"Draft Post Content:\n{body_text}"

    # Configure client with reasonable connection/read timeouts
    boto_config = Config(
        connect_timeout=5,
        read_timeout=15,
        retries={'max_attempts': 2}
    )

    try:
        client = boto3.client(
            'bedrock-runtime',
            region_name=settings.AWS_REGION,
            config=boto_config
        )

        response = client.converse(
            modelId=settings.BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_message}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "temperature": 0.7,
                "maxTokens": 600,
            }
        )

        # Extract text response from Converse output
        content_blocks = response.get('output', {}).get('message', {}).get('content', [])
        if not content_blocks or 'text' not in content_blocks[0]:
            raise AISuggestionError("Received empty response from Amazon Bedrock.")

        raw_text = content_blocks[0]['text'].strip()

        # Clean optional markdown code block fences (e.g. ```json ... ```)
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        data = json.loads(raw_text)

        # Schema validation
        if not isinstance(data.get('titles'), list) or not data['titles']:
            raise AISuggestionError("AI output missing 'titles' list.")
        if not isinstance(data.get('hashtags'), list) or not data['hashtags']:
            raise AISuggestionError("AI output missing 'hashtags' list.")
        if not isinstance(data.get('summary'), str):
            raise AISuggestionError("AI output missing 'summary' string.")

        # Clean tags (strip '#' and whitespace)
        data['hashtags'] = [
            str(tag).strip().lstrip('#').lower() 
            for tag in data['hashtags'] 
            if tag
        ]

        return {
            "titles": data['titles'][:5],
            "hashtags": data['hashtags'][:8],
            "summary": data['summary'][:300],
        }

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"Amazon Bedrock ClientError ({error_code}): {error_msg}")
        raise AISuggestionError(f"Bedrock service error ({error_code}): {error_msg}")
    except (BotoCoreError, Exception) as e:
        logger.error(f"Bedrock invocation failed: {str(e)}")
        raise AISuggestionError(f"Failed to generate suggestions: {str(e)}")


def get_ai_suggestions(body_text: str) -> Dict[str, Any]:
    """
    Main entry point for AI suggestions.
    Enforces input length validation, decides between mock and Bedrock modes,
    and returns a structured payload.
    """
    cleaned_body = body_text.strip()
    if len(cleaned_body) < 30:
        raise AISuggestionError("Please write at least 30 characters in the post body before requesting AI suggestions.")
    if len(cleaned_body) > 10000:
        raise AISuggestionError("Post body exceeds 10,000 characters limit for AI suggestion.")

    if getattr(settings, 'AI_MOCK_MODE', True):
        suggestions = _generate_mock_suggestions(cleaned_body)
        mode = "mock"
    else:
        suggestions = _invoke_bedrock(cleaned_body)
        mode = "bedrock"

    return {
        "mode": mode,
        "model": settings.BEDROCK_MODEL_ID,
        "suggestions": suggestions,
    }

