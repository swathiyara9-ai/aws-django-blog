from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify
from django.db.models import Q

from .models import Post
from .forms import PostForm


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


class PostDetailView(DetailView):
    """Display a single post found by its slug. Drafts visible only to author."""
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            # Authors can see their own drafts; everyone else only sees published posts
            return Post.objects.filter(Q(status='published') | Q(author=self.request.user)).distinct()
        return Post.objects.filter(status='published')


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
