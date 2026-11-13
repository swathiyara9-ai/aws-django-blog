from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import JsonResponse


def health_check(request):
    """
    Health check endpoint for the AWS Application Load Balancer (ALB).
    Returns HTTP 200 OK with JSON status so the ALB knows this instance is healthy.
    """
    return JsonResponse({
        "status": "ok",
        "app": "aws-django-blog"
    })


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('ai/', include('ai_assist.urls')),
    path('', include('blog.urls')),
    # Serve user-uploaded media files locally (works under both DEBUG=True and DEBUG=False).
    # In AWS production (Phase 8), django-storages will serve media directly via Amazon S3 / CloudFront.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
