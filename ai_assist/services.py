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


# Comprehensive stop words set to keep mock hashtags and titles clean and content-focused
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn', 'it', 'its', 'itself', 'just', 'like', 'lot',
    'make', 'many', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off',
    'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 's', 'same',
    'she', 'should', 'so', 'some', 'such', 't', 'than', 'that', 'the', 'their', 'theirs', 'them',
    'themselves', 'then', 'there', 'these', 'they', "they're", 'theyre', 'this', 'those', 'through',
    'time', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn', 'we', 'were', 'what', 'when',
    'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'won', 'would', 'you', 'your',
    'yours', 'yourself', 'yourselves', 'really', 'also', 'much', 'even', 'first', 'get', 'well'
}

TECH_KEYWORDS = {
    'aws', 'cloud', 'django', 'python', 'software', 'code', 'database', 'sql', 'postgres',
    'api', 'docker', 'kubernetes', 'linux', 'server', 'devops', 'backend', 'frontend',
    'framework', 'architecture', 'deploy', 'deployment', 'programming', 'developer',
    'git', 'ci', 'cd', 'security', 'bedrock', 'terraform', 'infrastructure', 'web'
}


def _extract_keywords(text: str, max_words: int = 8) -> List[str]:
    """Helper to extract clean, non-stopword keywords from text for content-aware mock suggestions."""
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower()
    words = cleaned.split()
    seen = set()
    keywords = []
    for w in words:
        if len(w) >= 3 and w not in STOP_WORDS and not w.isdigit():
            if w not in seen:
                seen.add(w)
                keywords.append(w)
            if len(keywords) >= max_words:
                break
    return keywords or ['insights', 'perspective', 'thoughts', 'notes', 'journal']


def _generate_mock_suggestions(body_text: str) -> Dict[str, Any]:
    """
    Generate realistic, content-aware mock suggestions without calling AWS.
    Produces 4 distinct title styles (statement, question, short headline, story-style)
    tailored to the user's first sentence and nouns, without tech boilerplate unless text is about technology.
    """
    keywords = _extract_keywords(body_text)

    # Extract first sentence
    sentences = [s.strip() for s in re.split(r'[.!?\n]+', body_text.strip()) if s.strip()]
    first_sentence = sentences[0] if sentences else body_text.strip()

    # Clean first sentence words for headline extraction
    first_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', first_sentence).split() if w.lower() not in STOP_WORDS]

    topic_1 = keywords[0].capitalize() if keywords else "Reflection"
    topic_2 = keywords[1].capitalize() if len(keywords) > 1 else (keywords[0].capitalize() if keywords else "Ideas")
    core_phrase = " ".join(first_words[:4]).title() if len(first_words) >= 2 else f"{topic_1} and {topic_2}"

    # Determine if text is tech-related
    body_lower = body_text.lower()
    is_tech = any(tk in body_lower for tk in TECH_KEYWORDS)

    if is_tech:
        # Tech-specific styles
        t1 = f"{core_phrase}: Understanding {topic_1}"
        t2 = f"How Does {topic_1} Really Work in Practice?"
        t3 = f"Demystifying {topic_1} and {topic_2}"
        t4 = f"Lessons Learned While Working with {topic_1}"
    else:
        # General / narrative styles (no forced tech buzzwords)
        t1 = f"{core_phrase}: A Closer Look at {topic_1}"
        t2 = f"Why {topic_1} Matters More Than We Think"
        t3 = f"Understanding {topic_1}: Key Takeaways"
        t4 = f"Reflections on {topic_1}: A Personal Perspective"

    titles = [t1, t2, t3, t4]

    # Clean hashtags (5-8 items, lowercase without '#', no stop words)
    tags = [k.lower() for k in keywords if len(k) <= 20]
    if len(tags) < 5:
        fallback = ['cloud', 'aws', 'django', 'python', 'webdev'] if is_tech else ['learning', 'thoughts', 'perspective', 'notes', 'updates']
        for fb in fallback:
            if fb not in tags:
                tags.append(fb)
            if len(tags) >= 6:
                break
    hashtags = tags[:8]

    # Summary: author's first sentence trimmed to 150 characters
    summary = (first_sentence[:147] + "...") if len(first_sentence) > 150 else first_sentence

    return {
        "titles": titles,
        "hashtags": hashtags,
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
                "temperature": 0.5,
                "maxTokens": 400,
            }
        )

        # Extract text response from Converse output
        content_blocks = response.get('output', {}).get('message', {}).get('content', [])
        if not content_blocks or 'text' not in content_blocks[0]:
            raise AISuggestionError("Received empty response from Amazon Bedrock.")

        raw_text = content_blocks[0]['text'].strip()

        # Find the first '{' to ignore conversational greetings or leading code fences
        start_idx = raw_text.find('{')
        if start_idx == -1:
            raise AISuggestionError("No valid JSON object found in AI response.")

        # Parse exactly one complete JSON object from the opening brace
        try:
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(raw_text[start_idx:])
        except json.JSONDecodeError:
            raise AISuggestionError("AI returned an invalid JSON response. Please try again.")

        # Schema & count validation
        if not isinstance(data, dict):
            raise AISuggestionError("AI response was not a valid JSON object.")

        titles = data.get('titles')
        if not isinstance(titles, list) or not titles:
            raise AISuggestionError("AI output missing or invalid 'titles' list.")

        hashtags = data.get('hashtags')
        if not isinstance(hashtags, list) or not hashtags:
            raise AISuggestionError("AI output missing or invalid 'hashtags' list.")

        summary = data.get('summary')
        if not isinstance(summary, str) or not summary.strip():
            raise AISuggestionError("AI output missing or invalid 'summary' string.")

        # Clean and validate contents
        clean_titles = [str(t).strip() for t in titles if str(t).strip()]
        if not clean_titles:
            raise AISuggestionError("AI output did not contain valid title strings.")

        clean_tags = [
            str(tag).strip().lstrip('#').lower() 
            for tag in hashtags 
            if str(tag).strip()
        ]
        if not clean_tags:
            raise AISuggestionError("AI output did not contain valid hashtag strings.")

        return {
            "titles": clean_titles[:5],
            "hashtags": clean_tags[:8],
            "summary": str(summary).strip()[:300],
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
        "region": settings.AWS_REGION,
        "suggestions": suggestions,
    }

