from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from blog.models import Post
from .models import PostView, PostStats
from .utils import get_visitor_hash


TRENDING_CACHE_KEY = 'top_10_trending'
PREVIOUS_RANKS_CACHE_KEY = 'trending_previous_ranks'


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
        # Immediately update PostStats for this post
        update_single_post_stats(post)
        return True
    return False


def calculate_post_score(post, now=None):
    """
    Helper to compute time-decayed trending score for a single post.
    Formula:
        score = (views + 3*comments + 2*likes) / (hours_since_published + 2) ^ 1.5
    """
    if now is None:
        now = timezone.now()
    views_count = post.views.count()
    comments_count = post.comments.filter(is_approved=True).count()
    likes_count = post.likes.count()

    age_seconds = max(0.0, (now - post.created_at).total_seconds())
    hours_since_published = age_seconds / 3600.0

    numerator = views_count + (3 * comments_count) + (2 * likes_count)
    denominator = (hours_since_published + 2) ** 1.5
    score = round(numerator / denominator, 4)

    return views_count, comments_count, likes_count, hours_since_published, score


def update_single_post_stats(post):
    """
    Update PostStats for one post immediately when it receives a view, comment, or like.
    Invalidates the top 10 trending cache so the next request recomputes rankings.
    """
    if post.status != 'published':
        return None

    views_count, comments_count, likes_count, _, score = calculate_post_score(post)
    stats, _ = PostStats.objects.update_or_create(
        post=post,
        defaults={
            'views': views_count,
            'likes': likes_count,
            'comments': comments_count,
            'score': score,
        }
    )
    # Invalidate top 10 trending cache
    cache.delete(TRENDING_CACHE_KEY)
    return stats


def compute_trending_scores():
    """
    Recalculate activity metrics and trending scores for all published posts.
    """
    now = timezone.now()
    published_posts = Post.objects.filter(status='published')
    updated_stats = []

    for post in published_posts:
        views_count, comments_count, likes_count, _, score = calculate_post_score(post, now=now)
        stats, _ = PostStats.objects.update_or_create(
            post=post,
            defaults={
                'views': views_count,
                'likes': likes_count,
                'comments': comments_count,
                'score': score,
            }
        )
        updated_stats.append(stats)

    # Invalidate top 10 trending cache
    cache.delete(TRENDING_CACHE_KEY)
    return updated_stats


def get_top_trending(limit=10):
    """
    Retrieve the top trending posts, cached for 30 seconds.
    Computes rank changes compared to the previously cached rank.
    """
    cached = cache.get(TRENDING_CACHE_KEY)
    if cached is not None:
        return cached

    now = timezone.now()
    qs = PostStats.objects.select_related('post', 'post__author').filter(
        post__status='published'
    ).order_by('-score')[:limit]

    previous_ranks = cache.get(PREVIOUS_RANKS_CACHE_KEY) or {}
    new_ranks = {}
    trending_data = []

    for index, item in enumerate(qs, start=1):
        post = item.post
        age_hours = round(max(0.0, (now - post.created_at).total_seconds()) / 3600.0, 1)
        prev_rank = previous_ranks.get(post.id)
        if prev_rank is None:
            rank_change = 0
        else:
            rank_change = prev_rank - index

        new_ranks[post.id] = index
        trending_data.append({
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'author': post.author.username,
            'views': item.views,
            'comments': item.comments,
            'likes': item.likes,
            'age_hours': age_hours,
            'score': item.score,
            'rank': index,
            'rank_change': rank_change,
        })

    cache.set(TRENDING_CACHE_KEY, trending_data, timeout=30)
    cache.set(PREVIOUS_RANKS_CACHE_KEY, new_ranks, timeout=3600)
    return trending_data
