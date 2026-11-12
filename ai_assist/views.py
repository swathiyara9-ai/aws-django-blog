import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.cache import cache
from blog.models import Tag
from .services import get_ai_suggestions, AISuggestionError


@login_required
@require_POST
def suggest_view(request):
    """
    API endpoint for AI suggestions.
    Accepts JSON payload: {"body": "..."}
    Returns JSON: {"success": True, "mode": "mock"|"bedrock", "suggestions": {...}}
    """
    # 1. Rate Limiting: Max 5 requests per minute per user
    cache_key = f"ai_rate_limit_{request.user.id}"
    request_count = cache.get(cache_key, 0)
    if request_count >= 5:
        return JsonResponse({
            "success": False,
            "error": "Rate limit exceeded: Please wait a minute before requesting more suggestions."
        }, status=429)

    # 2. Parse request payload
    try:
        data = json.loads(request.body.decode('utf-8'))
        body_text = data.get('body', '')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON payload."
        }, status=400)

    # 3. Generate suggestions
    try:
        result = get_ai_suggestions(body_text)
        cache.set(cache_key, request_count + 1, timeout=60)

        return JsonResponse({
            "success": True,
            "mode": result["mode"],
            "model": result["model"],
            "suggestions": result["suggestions"],
        })
    except AISuggestionError as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)
    except Exception as e:
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
