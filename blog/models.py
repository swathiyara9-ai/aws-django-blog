from django.db import models
from django.contrib.auth.models import User


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        # Enforce lowercase and strip any leading '#'
        if self.name:
            self.name = self.name.strip().lstrip('#').lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.name}"


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField()
    summary = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to='posts/', blank=True)
    image_alt = models.CharField(max_length=255, blank=True)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Automatically extract and store image dimensions to prevent layout jumps in masonry feeds
        if self.image:
            try:
                from PIL import Image
                # Seek to beginning in case file pointer was previously read
                if hasattr(self.image, 'file') and hasattr(self.image.file, 'seek'):
                    self.image.file.seek(0)
                with Image.open(self.image) as img:
                    self.image_width, self.image_height = img.size
                if hasattr(self.image, 'file') and hasattr(self.image.file, 'seek'):
                    self.image.file.seek(0)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_user_like')
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"
