import json
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.cache import cache
from blog.models import Tag
from cloudlog.tracker import CloudTracker, get_db_service_label
from .services import get_ai_suggestions, AISuggestionError


@login_required
@require_POST
def suggest_view(request):
    """
    API endpoint for AI suggestions.
    Accepts JSON payload: {"body": "..."}
    Returns JSON: {"success": True, "mode": "mock"|"bedrock", "suggestions": {...}}
    """
    tracker = CloudTracker(action="ai_suggest", user=request.user)

    with tracker.step("Django/Gunicorn", "Parsed payload & evaluated user rate limits"):
        # 1. Rate Limiting: Max 5 requests per minute per user
        cache_key = f"ai_rate_limit_{request.user.id}"
        request_count = cache.get(cache_key, 0)
        if request_count >= 5:
            tracker.save()
            return JsonResponse({
                "success": False,
                "error": "Rate limit exceeded: Please wait a minute before requesting more suggestions."
            }, status=429)

        # 2. Parse request payload
        try:
            data = json.loads(request.body.decode('utf-8'))
            body_text = data.get('body', '')
        except (json.JSONDecodeError, UnicodeDecodeError):
            tracker.save()
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON payload."
            }, status=400)

    # 3. Generate suggestions
    try:
        ai_service = "Mock AI" if getattr(settings, 'AI_MOCK_MODE', True) else "Bedrock"
        with tracker.step(ai_service, "Generated AI titles, hashtags, and summary", detail=f"model: {settings.BEDROCK_MODEL_ID}"):
            result = get_ai_suggestions(body_text)

        with tracker.step(get_db_service_label(), "Updated rate-limit counter in cache"):
            cache.set(cache_key, request_count + 1, timeout=60)

        tracker.save()
        return JsonResponse({
            "success": True,
            "mode": result["mode"],
            "model": result["model"],
            "region": result.get("region", getattr(settings, "AWS_REGION", "ap-southeast-2")),
            "suggestions": result["suggestions"],
        })
    except AISuggestionError as e:
        tracker.save()
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)
    except Exception as e:
        tracker.save()
        return JsonResponse({
            "success": False,
            "error": "An unexpected error occurred while generating suggestions."
        }, status=500)


@login_required
@require_POST
def ensure_tag_view(request):
    """
    Ensure a tag exists in the database so it can be dynamically selected in the post form.
    Accepts JSON: {"tag": "kubernetes"}
    Returns JSON: {"success": True, "id": tag.id, "name": tag.name}
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        raw_name = data.get('tag', '').strip()
        clean_name = raw_name.lstrip('#').strip().lower()
        if not clean_name:
            return JsonResponse({'success': False, 'error': 'Tag name cannot be empty.'}, status=400)

        clean_name = clean_name[:50]
        tag, created = Tag.objects.get_or_create(name=clean_name)
        return JsonResponse({
            'success': True,
            'id': tag.id,
            'name': tag.name,
            'created': created
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
