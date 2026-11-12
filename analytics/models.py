from django.db import models
from django.contrib.auth.models import User
from blog.models import Post


class PostView(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='post_views')
    visitor_hash = models.CharField(max_length=64, db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['post', 'viewed_at'], name='post_viewed_at_idx'),
            models.Index(fields=['visitor_hash', 'post'], name='visitor_post_idx'),
        ]

    def __str__(self):
        user_display = self.user.username if self.user else f"anon-{self.visitor_hash[:8]}"
        return f"View on '{self.post.title}' by {user_display} at {self.viewed_at:%Y-%m-%d %H:%M}"


class PostStats(models.Model):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, primary_key=True, related_name='stats')
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    score = models.FloatField(default=0.0, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score']
        verbose_name = 'Post Statistics'
        verbose_name_plural = 'Post Statistics'

    def __str__(self):
        return f"Stats for '{self.post.title}': score={self.score:.2f} (v={self.views}, l={self.likes}, c={self.comments})"
