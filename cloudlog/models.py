from django.db import models
from django.contrib.auth.models import User


class ActivityEvent(models.Model):
    ACTION_CHOICES = [
        ('post_created', 'Post Created'),
        ('post_updated', 'Post Updated'),
        ('post_deleted', 'Post Deleted'),
        ('comment_added', 'Comment Added'),
        ('liked', 'Post Liked'),
        ('viewed', 'Post Viewed'),
        ('ai_suggest', 'AI Suggestion'),
        ('trending_recomputed', 'Trending Recomputed'),
    ]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_events'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    post_id = models.IntegerField(null=True, blank=True)
    post_title = models.CharField(max_length=255, blank=True)
    steps = models.JSONField(default=list)  # list of {service, label, ms, detail}
    total_ms = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='activity_created_idx'),
            models.Index(fields=['action', '-created_at'], name='activity_action_idx'),
        ]

    def __str__(self):
        user_name = self.user.username if self.user else "Anonymous"
        return f"[{self.created_at:%H:%M:%S}] {self.action} by {user_name} ({self.total_ms:.1f}ms)"
