from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'body', 'summary', 'image', 'image_alt', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Write your post content here...'}),
            'summary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short summary (optional)'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_alt': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image alt description (for accessibility)'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'tags': 'Hold Ctrl (Windows) or Cmd (Mac) to select multiple tags.',
            'image': 'Upload a cover image for your post (optional).',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a constructive comment...'}),
        }
        labels = {
            'body': '',
        }
