from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Post CRUD URLs
    path('', views.PostListView.as_view(), name='post_list'),
    path('post/new/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/edit/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<slug:slug>/delete/', views.PostDeleteView.as_view(), name='post_delete'),

    # Interaction URLs (Comments, Likes, Tags)
    path('post/<slug:slug>/comment/', views.post_comment, name='post_comment'),
    path('post/<slug:slug>/like/', views.post_like_toggle, name='post_like_toggle'),
    path('tag/<str:tag_name>/', views.TagPostListView.as_view(), name='tag_posts'),

    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
