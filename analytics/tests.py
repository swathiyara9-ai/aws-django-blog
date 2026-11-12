from datetime import timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.management import call_command
from django.urls import reverse
from io import StringIO

from blog.models import Post, Comment, Like
from analytics.models import PostView, PostStats
from analytics.services import record_post_view, compute_trending_scores
from analytics.utils import get_visitor_hash


class AnalyticsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='carol', password='password123')
        self.post = Post.objects.create(
            author=self.user,
            title='Analytics in Action',
            slug='analytics-in-action',
            body='Studying cloud metrics.',
            status='published'
        )

    def test_visitor_hash_generation(self):
        """Visitor hash generates a 64-character SHA-256 string, never storing raw IP."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 TestBrowser'
        
        vhash = get_visitor_hash(request)
        self.assertEqual(len(vhash), 64)
        self.assertNotIn('192.168.1.100', vhash)

    def test_view_recording_and_deduplication(self):
        """First visit records view; second visit within 30 minutes is ignored."""
        request = self.factory.get(f'/post/{self.post.slug}/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'Chrome'

        # First visit
        recorded = record_post_view(request, self.post, window_minutes=30)
        self.assertTrue(recorded)
        self.assertEqual(PostView.objects.filter(post=self.post).count(), 1)

        # Immediate repeat visit (same IP + User-Agent)
        recorded_repeat = record_post_view(request, self.post, window_minutes=30)
        self.assertFalse(recorded_repeat)
        self.assertEqual(PostView.objects.filter(post=self.post).count(), 1)

    def test_draft_post_does_not_record_views(self):
        """Draft posts should never record views."""
        draft = Post.objects.create(
            author=self.user,
            title='Draft Article',
            slug='draft-article',
            body='Secret draft.',
            status='draft'
        )
        request = self.factory.get(f'/post/{draft.slug}/')
        request.user = self.user
        
        recorded = record_post_view(request, draft)
        self.assertFalse(recorded)
        self.assertEqual(PostView.objects.filter(post=draft).count(), 0)

    def test_compute_trending_scores_formula(self):
        """Verify the formula: score = (views + 3*comments + 2*likes) / (hours + 2)^1.5"""
        # Add 10 views
        for i in range(10):
            PostView.objects.create(post=self.post, visitor_hash=f'hash_{i}')
        
        # Add 2 comments
        for i in range(2):
            Comment.objects.create(post=self.post, author=self.user, body=f'Comment {i}')
            
        # Add 1 like
        Like.objects.create(post=self.post, user=self.user)

        compute_trending_scores()

        stats = PostStats.objects.get(post=self.post)
        self.assertEqual(stats.views, 10)
        self.assertEqual(stats.comments, 2)
        self.assertEqual(stats.likes, 1)

        # Expected score:
        # numerator = 10 + (3 * 2) + (2 * 1) = 18
        # hours ~ 0, denominator ~ (0 + 2)^1.5 = 2.828427
        # expected score = 18 / 2.828427 ~ 6.36
        self.assertGreater(stats.score, 6.0)
        self.assertLess(stats.score, 6.5)

    def test_compute_trending_management_command(self):
        """Management command runs cleanly and updates statistics."""
        out = StringIO()
        call_command('compute_trending', stdout=out)
        output = out.getvalue()
        
        self.assertIn("Successfully computed trending scores", output)
        self.assertTrue(PostStats.objects.filter(post=self.post).exists())

    def test_post_detail_view_triggers_record_view(self):
        """Navigating to post detail view in browser records view and updates count."""
        response = self.client.get(reverse('post_detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostView.objects.filter(post=self.post).count(), 1)
        self.assertContains(response, "1 view")
