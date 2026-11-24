import urllib.request
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Avg
from analytics.services import get_top_trending
from .models import ActivityEvent


def _get_imds_metadata():
    """
    Attempt to read instance metadata from EC2 IMDSv2 with 1-second timeout.
    Falls back gracefully to 'local' when running outside EC2.
    """
    try:
        # Request token for IMDSv2
        token_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
            method="PUT"
        )
        with urllib.request.urlopen(token_req, timeout=1.0) as resp:
            token = resp.read().decode('utf-8').strip()

        headers = {"X-aws-ec2-metadata-token": token}

        # Fetch Availability Zone
        az_req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/placement/availability-zone",
            headers=headers
        )
        with urllib.request.urlopen(az_req, timeout=1.0) as resp:
            az = resp.read().decode('utf-8').strip()

        # Fetch Instance ID
        inst_req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers=headers
        )
        with urllib.request.urlopen(inst_req, timeout=1.0) as resp:
            instance_id = resp.read().decode('utf-8').strip()

        region = az[:-1] if az else getattr(settings, 'AWS_REGION', 'ap-southeast-2')
        return {
            "environment": "ec2",
            "region": region,
            "availability_zone": az,
            "instance_id": instance_id,
        }
    except Exception:
        return {
            "environment": "local",
            "region": getattr(settings, 'AWS_REGION', 'ap-southeast-2'),
            "availability_zone": "local-workstation",
            "instance_id": "local-instance",
        }


def cloud_activity_api(request):
    """
    Public JSON API: returns latest 30 ActivityEvents.
    Supports ?after=<id> for incremental polling.
    """
    after_id = request.GET.get('after')
    qs = ActivityEvent.objects.all()

    if after_id and after_id.isdigit():
        qs = qs.filter(id__gt=int(after_id)).order_by('id')[:30]
    else:
        qs = qs.order_by('-created_at')[:30]

    events_data = []
    for event in qs:
        events_data.append({
            "id": event.id,
            "created_at": event.created_at.isoformat(),
            "user": event.user.username if event.user else "Anonymous",
            "action": event.action,
            "post_id": event.post_id,
            "post_title": event.post_title,
            "steps": event.steps,
            "total_ms": event.total_ms,
        })

    return JsonResponse({"events": events_data})


def trending_api(request):
    """
    Public JSON API: returns top 10 trending posts with rank change and stats.
    Cached for 30 seconds.
    """
    data = get_top_trending(limit=10)
    return JsonResponse({"trending": data})


def cloud_status_api(request):
    """
    Public JSON API: returns cloud infrastructure status.
    Provides region, AZ, and instance ID from IMDSv2 (or 'local'),
    database engine, bucket name, AI mode, and health status without leaking secrets.
    """
    imds = _get_imds_metadata()

    # Determine database engine safely without host/credentials
    engine_path = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'postgresql' in engine_path.lower():
        db_engine = "PostgreSQL (RDS)"
    elif 'mysql' in engine_path.lower():
        db_engine = "MySQL (RDS)"
    elif 'sqlite' in engine_path.lower():
        db_engine = "SQLite (local)"
    else:
        db_engine = engine_path.split('.')[-1]

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or 'None (local media/)'
    ai_mode = "mock" if getattr(settings, 'AI_MOCK_MODE', True) else "bedrock"
    ai_model = getattr(settings, 'BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')

    return JsonResponse({
        "environment": imds["environment"],
        "region": imds["region"],
        "availability_zone": imds["availability_zone"],
        "instance_id": imds["instance_id"],
        "database_engine": db_engine,
        "bucket_name": bucket_name,
        "ai_mode": ai_mode,
        "ai_model": ai_model,
        "health": "ok",
    })


def ai_insights_api(request):
    """
    Public JSON API: returns aggregated metrics for AI suggestions
    (total count, average latency, and mock vs bedrock distribution).
    """
    ai_events = ActivityEvent.objects.filter(action='ai_suggest')
    total_count = ai_events.count()
    avg_latency = ai_events.aggregate(Avg('total_ms'))['total_ms__avg'] or 0.0

    mock_count = 0
    bedrock_count = 0

    for event in ai_events:
        is_bedrock = False
        for step in event.steps:
            service = step.get('service', '').lower()
            detail = step.get('detail', '').lower()
            if 'bedrock' in service or 'mode: bedrock' in detail:
                is_bedrock = True
                break
        if is_bedrock:
            bedrock_count += 1
        else:
            mock_count += 1

    return JsonResponse({
        "total_suggestions": total_count,
        "average_latency_ms": round(avg_latency, 2),
        "mock_count": mock_count,
        "bedrock_count": bedrock_count,
    })
