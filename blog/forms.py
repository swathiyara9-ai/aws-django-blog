import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Post, Comment, Tag


class PostForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Type hashtags and press Enter, comma, or space to add chips (max 10)."
    )

    class Meta:
        model = Post
        fields = ['title', 'body', 'summary', 'image', 'image_alt', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Write your post content here...'}),
            'summary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short summary (optional)'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_alt': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image alt description (for accessibility)'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'image': 'Upload a cover image for your post (optional).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-fill initial tags as comma-separated string for edit mode
            self.initial['tags'] = ', '.join(self.instance.tags.values_list('name', flat=True))

    def clean_tags(self):
        raw_tags = self.cleaned_data.get('tags')
        # Check self.data in case tags was submitted as a list (e.g. from tests)
        if not raw_tags and self.data:
            raw_data = self.data.getlist('tags') if hasattr(self.data, 'getlist') else self.data.get('tags')
            if raw_data:
                raw_tags = raw_data

        if not raw_tags:
            self._tag_objs = []
            return ""

        # Normalize incoming raw_tags: supports lists of IDs/strings or comma-separated strings
        tokens = []
        if isinstance(raw_tags, (list, tuple)):
            for item in raw_tags:
                if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                    # Backward compatibility for existing tests passing tag ID: [tag.id]
                    tag_obj = Tag.objects.filter(id=int(item)).first()
                    if tag_obj:
                        tokens.append(tag_obj.name)
                elif isinstance(item, str):
                    for sub in re.split(r'[, ]+', item):
                        if sub.strip():
                            tokens.append(sub.strip())
        elif isinstance(raw_tags, str):
            for sub in re.split(r'[, ]+', raw_tags):
                if sub.strip():
                    tokens.append(sub.strip())

        cleaned_names = []
        seen = set()

        for token in tokens:
            # 1. Strip leading '#' and whitespace, lowercase
            norm = token.strip().lstrip('#').strip().lower()
            if not norm:
                continue

            # 2. Validate max length 50
            if len(norm) > 50:
                raise ValidationError(f"Tag '#{norm}' exceeds the 50-character limit.")

            # 3. Validate characters: letters, digits, and underscores
            if not re.match(r'^[a-z0-9_]+$', norm):
                raise ValidationError(f"Invalid tag '#{norm}'. Tags can only contain letters, numbers, and underscores.")

            # 4. Deduplicate preserving order
            if norm not in seen:
                seen.add(norm)
                cleaned_names.append(norm)

        # 5. Limit to 10 tags per post
        if len(cleaned_names) > 10:
            raise ValidationError("A post can have at most 10 tags.")

        # 6. Resolve Tag instances using get_or_create
        tag_objs = []
        for name in cleaned_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objs.append(tag)

        return tag_objs




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
