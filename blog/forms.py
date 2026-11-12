from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'body', 'summary', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Write your post content here...'}),
            'summary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short summary (optional)'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'tags': 'Hold Ctrl (Windows) or Cmd (Mac) to select multiple tags.',
        }

