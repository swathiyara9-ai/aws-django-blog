from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Post, Tag


class PostCRUDAndAuthTests(TestCase):
    def setUp(self):
        # Create two distinct users
        self.author = User.objects.create_user(username='alice', password='password123')
        self.other_user = User.objects.create_user(username='bob', password='password123')
        
        # Create a tag
        self.tag = Tag.objects.create(name='python')

        # Create published post by author
        self.published_post = Post.objects.create(
            author=self.author,
            title='Alice Published Post',
            slug='alice-published-post',
            body='This is a published post content.',
            summary='Published summary',
            status='published'
        )
        self.published_post.tags.add(self.tag)

        # Create draft post by author
        self.draft_post = Post.objects.create(
            author=self.author,
            title='Alice Draft Post',
            slug='alice-draft-post',
            body='This is a secret draft.',
            status='draft'
        )

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
            'tags': [self.tag.id],
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
            'tags': [self.tag.id],
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
        # Anonymous user gets 404
        anon_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(anon_response.status_code, 404)

        # Other logged in user gets 404
        self.client.login(username='bob', password='password123')
        bob_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(bob_response.status_code, 404)

        # Author can view draft
        self.client.login(username='alice', password='password123')
        author_response = self.client.get(reverse('post_detail', kwargs={'slug': self.draft_post.slug}))
        self.assertEqual(author_response.status_code, 200)
        self.assertContains(author_response, 'Draft Preview')
