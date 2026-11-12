from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from blog.models import Post
from .models import PostView, PostStats
from .utils import get_visitor_hash


def record_post_view(request, post, window_minutes=30):
    """
    Record a view for a published post with de-duplication.
    Ignores repeated views from the same visitor within the specified window (default 30 mins).
    """
    if post.status != 'published':
        return False

    visitor_hash = get_visitor_hash(request)
    user = request.user if request.user.is_authenticated else None
    cutoff_time = timezone.now() - timedelta(minutes=window_minutes)

    # Check for recent view by this visitor for this post
    recent_view = PostView.objects.filter(
        post=post,
        visitor_hash=visitor_hash,
        viewed_at__gte=cutoff_time
    ).exists()

    if not recent_view:
        PostView.objects.create(
            post=post,
            user=user,
            visitor_hash=visitor_hash
        )
        return True
    return False


def compute_trending_scores():
    """
    Recalculate activity metrics and trending scores for all published posts.
    
    Formula:
        score = (views + 3*comments + 2*likes) / (hours_since_published + 2) ^ 1.5
    """
    now = timezone.now()
    published_posts = Post.objects.filter(status='published')
    updated_stats = []

    for post in published_posts:
        views_count = post.views.count()
        comments_count = post.comments.filter(is_approved=True).count()
        likes_count = post.likes.count()

        # Calculate post age in hours
        age_seconds = max(0.0, (now - post.created_at).total_seconds())
        hours_since_published = age_seconds / 3600.0

        # Calculate time-decayed trending score
        numerator = views_count + (3 * comments_count) + (2 * likes_count)
        denominator = (hours_since_published + 2) ** 1.5
        score = round(numerator / denominator, 4)

        stats, created = PostStats.objects.update_or_create(
            post=post,
            defaults={
                'views': views_count,
                'likes': likes_count,
                'comments': comments_count,
                'score': score,
            }
        )
        updated_stats.append(stats)

    return updated_stats

