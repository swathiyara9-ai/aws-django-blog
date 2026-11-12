from io import BytesIO
from PIL import Image
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Post, Tag, Comment, Like


def get_test_image():
    file = BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(file, 'jpeg')
    file.seek(0)
    return SimpleUploadedFile('test.jpg', file.read(), content_type='image/jpeg')


class PostCRUDAndAuthTests(TestCase):
    def setUp(self):
        # Create two distinct users
        self.author = User.objects.create_user(username='alice', password='password123')
        self.other_user = User.objects.create_user(username='bob', password='password123')
        
        # Create tags
        self.tag_python = Tag.objects.create(name='python')
        self.tag_aws = Tag.objects.create(name='aws')

        # Create published post by author
        self.published_post = Post.objects.create(
            author=self.author,
            title='Alice Published Post',
            slug='alice-published-post',
            body='This is a published post content.',
            summary='Published summary',
            status='published'
        )
        self.published_post.tags.add(self.tag_python)

        # Create draft post by author
        self.draft_post = Post.objects.create(
            author=self.author,
            title='Alice Draft Post',
            slug='alice-draft-post',
            body='This is a secret draft.',
            status='draft'
        )
        self.draft_post.tags.add(self.tag_python)

    # --- Phase 2: CRUD & Auth Tests ---

    def test_post_list_shows_only_published_posts(self):
        """Published posts appear in post list; drafts do not."""
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Published Post')
        self.assertNotContains(response, 'Alice Draft Post')

    def test_anonymous_user_cannot_access_create_view(self):
        """Logged-out user is redirected to login when trying to create a post."""
        response = self.client.get(reverse('post_create'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_logged_in_user_can_create_post_with_auto_slug(self):
        """Authenticated user can create post; author is set and slug is generated."""
        self.client.login(username='alice', password='password123')
        post_data = {
            'title': 'New Test Post Title',
            'body': 'Content of the new post.',
            'summary': 'Summary text.',
            'tags': [self.tag_python.id],
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify post created in DB
        created_post = Post.objects.get(title='New Test Post Title')
        self.assertEqual(created_post.author, self.author)
        self.assertEqual(created_post.slug, 'new-test-post-title')
        self.assertContains(response, 'created successfully')

    def test_author_can_edit_own_post(self):
        """Author can update their own post."""
        self.client.login(username='alice', password='password123')
        update_data = {
            'title': 'Alice Published Post Updated',
            'body': 'Updated body content.',
            'summary': 'Updated summary.',
            'tags': [self.tag_python.id],
            'status': 'published'
        }
        response = self.client.post(
            reverse('post_update', kwargs={'slug': self.published_post.slug}),
            data=update_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.published_post.refresh_from_db()
        self.assertEqual(self.published_post.title, 'Alice Published Post Updated')
        self.assertContains(response, 'updated successfully')

    def test_non_author_gets_403_when_editing_post(self):
        """Non-author user gets 403 Forbidden when trying to edit someone else's post."""
        self.client.login(username='bob', password='password123')
        response = self.client.get(reverse('post_update', kwargs={'slug': self.published_post.slug}))
        self.assertEqual(response.status_code, 403)

    def test_non_author_gets_403_when_deleting_post(self):
        """Non-author user gets 403 Forbidden when trying to delete someone else's post."""
        self.client.login(username='bob', password='password123')
        response = self.client.get(reverse('post_delete', kwargs={'slug': self.published_post.slug}))
        self.assertEqual(response.status_code, 403)

    def test_author_can_delete_own_post(self):
        """Author can delete their own post."""
        self.client.login(username='alice', password='password123')
        response = self.client.post(
            reverse('post_delete', kwargs={'slug': self.published_post.slug}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(slug=self.published_post.slug).exists())
        self.assertContains(response, 'Post deleted successfully')

    def test_draft_post_visibility(self):
        """Draft posts can be viewed by the author, but return 404 to anonymous and other users."""
        anon_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(anon_response.status_code, 404)

        self.client.login(username='bob', password='password123')
        bob_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(bob_response.status_code, 404)

        self.client.login(username='alice', password='password123')
        author_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(author_response.status_code, 200)
        self.assertContains(author_response, 'Draft Preview')

    # --- Phase 3: Comments, Likes, Images, Tags Tests ---

    def test_anonymous_user_cannot_post_comment(self):
        """Anonymous user submitting comment is redirected to login."""
        response = self.client.post(
            reverse('post_comment', kwargs={'slug': self.published_post.slug}),
            data={'body': 'Great post!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
        self.assertEqual(self.published_post.comments.count(), 0)

    def test_logged_in_user_can_comment(self):
        """Authenticated user can comment, appearing on post detail."""
        self.client.login(username='bob', password='password123')
        response = self.client.post(
            reverse('post_comment', kwargs={'slug': self.published_post.slug}),
            data={'body': 'Awesome read from Bob!'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.published_post.comments.count(), 1)
        self.assertContains(response, 'Awesome read from Bob!')
        self.assertContains(response, 'Your comment has been posted!')

    def test_like_unlike_toggle(self):
        """Toggling like button creates and removes like; count updates accordingly."""
        self.client.login(username='bob', password='password123')
        like_url = reverse('post_like_toggle', kwargs={'slug': self.published_post.slug})

        # First click: Like
        res1 = self.client.post(like_url, follow=True)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(self.published_post.likes.count(), 1)
        self.assertContains(res1, 'Liked (1)')

        # Second click: Unlike
        res2 = self.client.post(like_url, follow=True)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(self.published_post.likes.count(), 0)
        self.assertContains(res2, 'Like (0)')

    def test_tag_filter_page(self):
        """Tag filter page lists published posts with that tag, but not others or drafts."""
        # Create a second post tagged with 'aws'
        aws_post = Post.objects.create(
            author=self.author,
            title='AWS Architecture Overview',
            slug='aws-architecture-overview',
            body='Cloud best practices.',
            status='published'
        )
        aws_post.tags.add(self.tag_aws)

        # Browse /tag/python/
        python_res = self.client.get(reverse('tag_posts', kwargs={'tag_name': 'python'}))
        self.assertEqual(python_res.status_code, 200)
        self.assertContains(python_res, 'Alice Published Post')
        self.assertNotContains(python_res, 'AWS Architecture Overview')
        self.assertNotContains(python_res, 'Alice Draft Post')

        # Browse /tag/aws/
        aws_res = self.client.get(reverse('tag_posts', kwargs={'tag_name': 'aws'}))
        self.assertEqual(aws_res.status_code, 200)
        self.assertContains(aws_res, 'AWS Architecture Overview')
        self.assertNotContains(aws_res, 'Alice Published Post')

    def test_post_image_upload(self):
        """Images can be uploaded when creating a post and display on list and detail."""
        self.client.login(username='alice', password='password123')
        image = get_test_image()
        post_data = {
            'title': 'Post With Cover Photo',
            'body': 'Photo description and text.',
            'summary': 'A visual summary.',
            'image': image,
            'image_alt': 'A blue test square',
            'tags': [self.tag_python.id],
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        post = Post.objects.get(title='Post With Cover Photo')
        self.assertTrue(bool(post.image))
        self.assertEqual(post.image_alt, 'A blue test square')
        self.assertContains(response, post.image.url)

        # Also check home page includes the thumbnail
        home_res = self.client.get(reverse('post_list'))
        self.assertContains(home_res, post.image.url)

        # Cleanup uploaded test file
        if post.image and hasattr(post.image, 'path'):
            import os
            if os.path.exists(post.image.path):
                os.remove(post.image.path)
