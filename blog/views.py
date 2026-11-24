from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.db.models import Q, Count
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse, HttpResponse

from cloudlog.tracker import CloudTracker, get_db_service_label
from analytics.services import record_post_view, update_single_post_stats, get_top_trending, TRENDING_CACHE_KEY
from analytics.models import PostStats
from .models import Post, Comment, Like, Tag
from .forms import PostForm, CommentForm


# --- Authentication Views ---

def register_view(request):
    """Register a new user and log them in automatically."""
    if request.user.is_authenticated:
        return redirect('post_list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to AWS Django Blog, {user.username}! Your account has been created.")
            return redirect('post_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# --- Post CRUD Views ---

class PostListView(ListView):
    """Display paginated list of published posts, newest first."""
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 16

    def get_queryset(self):
        # Optimized with select_related, prefetch_related, and annotations to eliminate N+1 queries
        return (
            Post.objects.filter(status='published')
            .select_related('author')
            .prefetch_related('tags')
            .annotate(
                likes_count=Count('likes', distinct=True),
                comments_count=Count('comments', distinct=True)
            )
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Map top 3 trending post IDs to their rank for the flame badges
        top_3 = get_top_trending(limit=3)
        trending_ranks = {item['id']: item['rank'] for item in top_3}
        posts_list = list(context['posts'])
        for post in posts_list:
            post.trending_rank = trending_ranks.get(post.id)
        context['trending_ranks'] = trending_ranks
        # 4 column containers for masonry feed on desktop
        context['col_0'] = posts_list[0::4]
        context['col_1'] = posts_list[1::4]
        context['col_2'] = posts_list[2::4]
        context['col_3'] = posts_list[3::4]
        return context


class PostDetailView(DetailView):
    """Display a single post found by its slug. Drafts visible only to author."""
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Post.objects.filter(Q(status='published') | Q(author=self.request.user)).distinct()
        return Post.objects.filter(status='published')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        tracker = CloudTracker(action="viewed", user=request.user, post_id=self.object.id, post_title=self.object.title)

        with tracker.step("Django/Gunicorn", "Resolved post by slug"):
            pass

        with tracker.step("Analytics", "Checked 30-min visitor fingerprint window"):
            recorded = record_post_view(request, self.object)

        if recorded:
            with tracker.step(get_db_service_label(), "Recorded new view row in DB"):
                pass
            with tracker.step("Trending", "Updated post score and refreshed cache"):
                pass

        tracker.save()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Approved comments, newest first
        context['comments'] = self.object.comments.filter(is_approved=True).select_related('author').order_by('-created_at', '-id')
        context['comment_form'] = CommentForm()
        context['likes_count'] = self.object.likes.count()
        context['views_count'] = self.object.views.count()
        context['user_has_liked'] = (
            self.object.likes.filter(user=self.request.user).exists()
            if self.request.user.is_authenticated else False
        )
        words_count = len(self.object.body.split())
        context['reading_time'] = max(1, (words_count + 199) // 200)
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Create a new post. Author is request.user, slug is auto-generated."""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        tracker = CloudTracker(action="post_created", user=self.request.user)
        with tracker.step("Django/Gunicorn", "Validated post form & generated unique slug"):
            form.instance.author = self.request.user
            base_slug = slugify(form.instance.title) or "post"
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            form.instance.slug = slug

        image_file = self.request.FILES.get('image')
        if image_file:
            with tracker.step("S3", f"Uploaded image: {image_file.name}", detail=f"{image_file.size / 1024:.1f} KB"):
                response = super().form_valid(form)
        else:
            with tracker.step(get_db_service_label(), "Saved post and relations to database"):
                response = super().form_valid(form)

        tracker.post_id = self.object.id
        tracker.post_title = self.object.title

        with tracker.step("Trending", "Initialized post statistics and score"):
            update_single_post_stats(self.object)

        event = tracker.save()
        total_ms = event.total_ms if event else 0
        steps_summary = ", ".join([f"{s.get('service', 'Service')} {s.get('ms', 0):.0f} ms" for s in tracker.steps if s.get('ms', 0) > 0]) or f"Cloud {total_ms:.1f} ms"
        msg = mark_safe(
            f"Post saved &mdash; '{self.object.title}' created successfully &middot; {steps_summary} "
            f"<a href='/cloud-activity/' class='alert-link text-info text-decoration-underline ms-1'>View in Cloud Activity</a>"
        )
        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse('post_detail', kwargs={'slug': self.object.slug})


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit an existing post. Only the author is allowed."""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def form_valid(self, form):
        post = self.get_object()
        tracker = CloudTracker(action="post_updated", user=self.request.user, post_id=post.id, post_title=form.instance.title)

        with tracker.step("Django/Gunicorn", "Validated update form & permissions"):
            pass

        image_file = self.request.FILES.get('image')
        if image_file:
            with tracker.step("S3", f"Uploaded updated image: {image_file.name}", detail=f"{image_file.size / 1024:.1f} KB"):
                response = super().form_valid(form)
        else:
            with tracker.step(get_db_service_label(), "Updated post record in database"):
                response = super().form_valid(form)

        with tracker.step("Trending", "Recalculated post statistics and score"):
            update_single_post_stats(self.object)

        event = tracker.save()
        total_ms = event.total_ms if event else 0
        steps_summary = ", ".join([f"{s.get('service', 'Service')} {s.get('ms', 0):.0f} ms" for s in tracker.steps if s.get('ms', 0) > 0]) or f"Cloud {total_ms:.1f} ms"
        msg = mark_safe(
            f"Post saved &mdash; '{self.object.title}' updated successfully &middot; {steps_summary} "
            f"<a href='/cloud-activity/' class='alert-link text-info text-decoration-underline ms-1'>View in Cloud Activity</a>"
        )
        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse('post_detail', kwargs={'slug': self.object.slug})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a post after confirmation. Only the author is allowed."""
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('post_list')

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def form_valid(self, form):
        post = self.get_object()
        tracker = CloudTracker(action="post_deleted", user=self.request.user, post_id=post.id, post_title=post.title)

        with tracker.step("Django/Gunicorn", "Verified author permissions"):
            pass

        with tracker.step(get_db_service_label(), "Deleted post record from database"):
            response = super().form_valid(form)

        with tracker.step("Trending", "Invalidated trending cache"):
            cache.delete(TRENDING_CACHE_KEY)

        event = tracker.save()
        total_ms = event.total_ms if event else 0
        steps_summary = ", ".join([f"{s.get('service', 'Service')} {s.get('ms', 0):.0f} ms" for s in tracker.steps if s.get('ms', 0) > 0]) or f"Cloud {total_ms:.1f} ms"
        msg = mark_safe(
            f"Post deleted successfully &mdash; {steps_summary} "
            f"<a href='/cloud-activity/' class='alert-link text-info text-decoration-underline ms-1'>View in Cloud Activity</a>"
        )
        messages.success(self.request, msg)
        return response


# --- Interaction Views (Comments, Likes, Tags) ---

@login_required
def post_comment(request, slug):
    """Submit a comment on a post."""
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        tracker = CloudTracker(action="comment_added", user=request.user, post_id=post.id, post_title=post.title)
        with tracker.step("Django/Gunicorn", "Validated comment form"):
            form = CommentForm(request.POST)

        if form.is_valid():
            with tracker.step(get_db_service_label(), "Saved comment to database"):
                comment = form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()

            with tracker.step("Trending", "Updated post stats & score"):
                update_single_post_stats(post)

            messages.success(request, "Your comment has been posted!")
        else:
            messages.error(request, "There was an issue with your comment. Please try again.")

        tracker.save()
    return redirect('post_detail', slug=post.slug)


@login_required
def post_like_toggle(request, slug):
    """Toggle a like for the current logged-in user on a post."""
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        tracker = CloudTracker(action="liked", user=request.user, post_id=post.id, post_title=post.title)
        with tracker.step(get_db_service_label(), "Checked and toggled like record in DB"):
            existing_like = Like.objects.filter(post=post, user=request.user).first()
            if existing_like:
                existing_like.delete()
                messages.info(request, "You unliked this post.")
            else:
                Like.objects.create(post=post, user=request.user)
                messages.success(request, "You liked this post!")

        with tracker.step("Trending", "Updated post stats & score"):
            update_single_post_stats(post)

        tracker.save()
    return redirect('post_detail', slug=post.slug)


class TagPostListView(ListView):
    """Display published posts associated with a specific tag."""
    model = Post
    template_name = 'blog/tag_post_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, name=self.kwargs['tag_name'].lower())
        # Optimized with select_related, prefetch_related, and annotations to eliminate N+1 queries
        return (
            Post.objects.filter(tags=self.tag, status='published')
            .select_related('author')
            .prefetch_related('tags')
            .annotate(
                likes_count=Count('likes', distinct=True),
                comments_count=Count('comments', distinct=True)
            )
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


# --- Infinite Feed, Search, and Full Telemetry Pages ---

def post_feed_api(request):
    """
    JSON feed endpoint for infinite vertical scroll.
    Returns next batch of 12 posts with image dimensions, counts, and top 3 flame ranks.
    """
    page_number = request.GET.get('page', 2)
    posts_qs = (
        Post.objects.filter(status='published')
        .select_related('author')
        .prefetch_related('tags')
        .annotate(
            likes_count=Count('likes', distinct=True),
            comments_count=Count('comments', distinct=True)
        )
        .order_by('-created_at')
    )
    paginator = Paginator(posts_qs, 16)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, ValueError):
        res = JsonResponse({'posts': [], 'has_next': False})
        res['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        res['Pragma'] = 'no-cache'
        return res

    top_3 = get_top_trending(limit=3)
    trending_ranks = {item['id']: item['rank'] for item in top_3}

    posts_data = []
    for post in page_obj:
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'summary': post.summary or (post.body[:120] + '...' if len(post.body) > 120 else post.body),
            'author': post.author.username,
            'created_at': post.created_at.strftime('%b %d, %Y'),
            'image_url': post.image.url if post.image else None,
            'image_alt': post.image_alt or post.title,
            'image_width': post.image_width,
            'image_height': post.image_height,
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'tags': [t.name for t in post.tags.all()],
            'trending_rank': trending_ranks.get(post.id),
        })

    response = JsonResponse({
        'posts': posts_data,
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
    })
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response


def favicon_view(request):
    """Return a tiny SVG cloud favicon to prevent 404 in console."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">☁️</text></svg>'
    return HttpResponse(svg, content_type="image/svg+xml")


def search_view(request):
    """Search title, body, and tags with masonry card feed results."""
    query = request.GET.get('q', '').strip()
    posts = Post.objects.none()
    col_0, col_1, col_2, col_3 = [], [], [], []
    if query:
        posts = (
            Post.objects.filter(
                Q(title__icontains=query) | Q(body__icontains=query) | Q(tags__name__icontains=query),
                status='published'
            )
            .select_related('author')
            .prefetch_related('tags')
            .annotate(
                likes_count=Count('likes', distinct=True),
                comments_count=Count('comments', distinct=True)
            )
            .distinct()
            .order_by('-created_at')
        )
        top_3 = get_top_trending(limit=3)
        trending_ranks = {item['id']: item['rank'] for item in top_3}
        posts_list = list(posts)
        for post in posts_list:
            post.trending_rank = trending_ranks.get(post.id)
        col_0 = posts_list[0::4]
        col_1 = posts_list[1::4]
        col_2 = posts_list[2::4]
        col_3 = posts_list[3::4]

    return render(request, 'blog/search_results.html', {
        'query': query,
        'posts': posts,
        'col_0': col_0,
        'col_1': col_1,
        'col_2': col_2,
        'col_3': col_3,
    })


def trending_page_view(request):
    """Full dedicated page for the trending analytics leaderboard."""
    trending_items = get_top_trending(limit=10)
    hero_trending = trending_items[:3]
    rest_trending = trending_items[3:]
    return render(request, 'blog/trending.html', {
        'hero_trending': hero_trending,
        'rest_trending': rest_trending,
        'all_trending': trending_items,
    })


def cloud_activity_page_view(request):
    """Full dedicated page for the cloud activity stream & timing pipeline."""
    return render(request, 'blog/cloud_activity.html')


def architecture_page_view(request):
    """Full dedicated page for the AWS architecture interactive map."""
    return render(request, 'blog/architecture.html')


def ai_insights_page_view(request):
    """Full dedicated page for AI insights and performance telemetry."""
    return render(request, 'blog/ai_insights.html')


def tag_autocomplete_api(request):
    """Return autocomplete suggestions for tags matching query 'q'."""
    query = request.GET.get('q', '').strip().lstrip('#').lower()
    if query:
        tags = Tag.objects.filter(name__icontains=query).values_list('name', flat=True)[:10]
    else:
        tags = Tag.objects.values_list('name', flat=True)[:10]
    return JsonResponse({'tags': list(tags)})



class UserSettingsView(LoginRequiredMixin, PasswordChangeView):
    """User account settings, profile information, and password change."""
    template_name = 'blog/settings.html'
    success_url = reverse_lazy('user_settings')

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed successfully!")
        return super().form_valid(form)

