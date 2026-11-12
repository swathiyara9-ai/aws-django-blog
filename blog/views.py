from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify
from django.db.models import Q

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
    paginate_by = 5

    def get_queryset(self):
        return Post.objects.filter(status='published').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from analytics.models import PostStats
        # Fetch top 5 trending posts with their statistics
        context['trending_stats'] = PostStats.objects.select_related('post').filter(
            post__status='published'
        ).order_by('-score')[:5]
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
        from analytics.services import record_post_view
        record_post_view(request, self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Approved comments, newest first
        context['comments'] = self.object.comments.filter(is_approved=True)
        context['comment_form'] = CommentForm()
        context['likes_count'] = self.object.likes.count()
        context['views_count'] = self.object.views.count()
        context['user_has_liked'] = (
            self.object.likes.filter(user=self.request.user).exists()
            if self.request.user.is_authenticated else False
        )
        return context


class PostCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new post. Author is request.user, slug is auto-generated."""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    success_message = "Post '%(title)s' created successfully!"

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # Auto-generate unique slug from title
        base_slug = slugify(form.instance.title)
        if not base_slug:
            base_slug = "post"
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        form.instance.slug = slug
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('post_detail', kwargs={'slug': self.object.slug})


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing post. Only the author is allowed."""
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_message = "Post '%(title)s' updated successfully!"

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

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
        messages.success(self.request, "Post deleted successfully.")
        return super().form_valid(form)


# --- Interaction Views (Comments, Likes, Tags) ---

@login_required
def post_comment(request, slug):
    """Submit a comment on a post."""
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, "Your comment has been posted!")
        else:
            messages.error(request, "There was an issue with your comment. Please try again.")
    return redirect('post_detail', slug=post.slug)


@login_required
def post_like_toggle(request, slug):
    """Toggle a like for the current logged-in user on a post."""
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        existing_like = Like.objects.filter(post=post, user=request.user).first()
        if existing_like:
            existing_like.delete()
            messages.info(request, "You unliked this post.")
        else:
            Like.objects.create(post=post, user=request.user)
            messages.success(request, "You liked this post!")
    return redirect('post_detail', slug=post.slug)


class TagPostListView(ListView):
    """Display published posts associated with a specific tag."""
    model = Post
    template_name = 'blog/tag_post_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, name=self.kwargs['tag_name'].lower())
        return Post.objects.filter(tags=self.tag, status='published').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context
