import json
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache

from blog.models import Post, Tag, Comment, Like
from analytics.models import PostStats
from analytics.services import (
    update_single_post_stats,
    get_top_trending,
    TRENDING_CACHE_KEY
)
from .models import ActivityEvent
from .tracker import CloudTracker, get_db_service_label


class CloudTrackerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        cache.clear()

    def test_tracker_records_real_timing_and_steps(self):
        """CloudTracker times each step with perf_counter and commits an ActivityEvent."""
        with CloudTracker(action="post_created", user=self.user, post_id=1, post_title="Test Post") as tracker:
            with tracker.step("Django/Gunicorn", "Form processing"):
                time.sleep(0.005)
            with tracker.step(get_db_service_label(), "Database insert"):
                time.sleep(0.005)

        event = ActivityEvent.objects.first()
        self.assertIsNotNone(event)
        self.assertEqual(event.action, "post_created")
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.post_id, 1)
        self.assertEqual(event.post_title, "Test Post")
        self.assertEqual(len(event.steps), 2)
        self.assertEqual(event.steps[0]["service"], "Django/Gunicorn")
        self.assertGreaterEqual(event.steps[0]["ms"], 4.0)
        self.assertEqual(event.steps[1]["service"], get_db_service_label())
        self.assertGreaterEqual(event.total_ms, 8.0)


class CloudAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sarah', password='password123')
        cache.clear()

        # Create published post
        self.post1 = Post.objects.create(
            author=self.user,
            title='First Cloud Architecture',
            slug='first-cloud-architecture',
            body='Detailed guide on AWS Django deployment.',
            status='published'
        )
        self.post2 = Post.objects.create(
            author=self.user,
            title='Second Cloud Architecture',
            slug='second-cloud-architecture',
            body='Another cloud post content.',
            status='published'
        )

    def test_cloud_activity_endpoint(self):
        """GET /api/cloud-activity/ returns serialized events with pagination support."""
        event1 = ActivityEvent.objects.create(
            user=self.user,
            action="post_created",
            post_id=self.post1.id,
            post_title=self.post1.title,
            steps=[{"service": "Django/Gunicorn", "label": "Parsed", "ms": 1.2, "detail": ""}],
            total_ms=1.5
        )
        event2 = ActivityEvent.objects.create(
            user=self.user,
            action="liked",
            post_id=self.post1.id,
            post_title=self.post1.title,
            steps=[{"service": "SQLite (local)", "label": "Liked", "ms": 2.1, "detail": ""}],
            total_ms=2.5
        )

        res = self.client.get(reverse('api_cloud_activity'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("events", data)
        self.assertEqual(len(data["events"]), 2)

        # Test pagination with ?after=<id>
        res_after = self.client.get(f"{reverse('api_cloud_activity')}?after={event1.id}")
        self.assertEqual(res_after.status_code, 200)
        data_after = res_after.json()
        self.assertEqual(len(data_after["events"]), 1)
        self.assertEqual(data_after["events"][0]["id"], event2.id)

    def test_trending_api_and_rank_change(self):
        """GET /api/trending/ returns top 10 with metrics, rank, and rank changes."""
        update_single_post_stats(self.post1)
        update_single_post_stats(self.post2)

        res = self.client.get(reverse('api_trending'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("trending", data)
        self.assertGreaterEqual(len(data["trending"]), 2)

        first_item = data["trending"][0]
        self.assertIn("views", first_item)
        self.assertIn("comments", first_item)
        self.assertIn("likes", first_item)
        self.assertIn("score", first_item)
        self.assertIn("rank", first_item)
        self.assertIn("rank_change", first_item)

        # Check caching: cached for 30 seconds
        self.assertIsNotNone(cache.get(TRENDING_CACHE_KEY))

        # Adding a like invalidates cache
        Like.objects.create(post=self.post2, user=self.user)
        update_single_post_stats(self.post2)
        self.assertIsNone(cache.get(TRENDING_CACHE_KEY))

    def test_cloud_status_endpoint_never_leaks_secrets(self):
        """GET /api/cloud-status/ reports environment status without exposing credentials."""
        res = self.client.get(reverse('api_cloud_status'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("environment"), ["local", "ec2"])
        self.assertEqual(data.get("health"), "ok")
        self.assertIn("database_engine", data)
        self.assertIn("bucket_name", data)
        self.assertIn("ai_mode", data)
        self.assertIn("ai_model", data)

        # Critical security check: No secrets leaked
        raw_body = res.content.decode('utf-8').lower()
        self.assertNotIn("password", raw_body)
        self.assertNotIn("secret", raw_body)

    def test_ai_insights_endpoint(self):
        """GET /api/ai-insights/ returns accurate aggregated counts and latency."""
        ActivityEvent.objects.create(
            user=self.user,
            action="ai_suggest",
            steps=[{"service": "Mock AI", "label": "Generated", "ms": 15.0, "detail": "mode: mock"}],
            total_ms=20.0
        )
        ActivityEvent.objects.create(
            user=self.user,
            action="ai_suggest",
            steps=[{"service": "Bedrock", "label": "Generated", "ms": 120.0, "detail": "mode: bedrock"}],
            total_ms=130.0
        )

        res = self.client.get(reverse('api_ai_insights'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_suggestions"], 2)
        self.assertEqual(data["average_latency_ms"], 75.0)
        self.assertEqual(data["mock_count"], 1)
        self.assertEqual(data["bedrock_count"], 1)


class QueryOptimizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='author1', password='password123')
        self.tag1 = Tag.objects.create(name='python')
        self.tag2 = Tag.objects.create(name='django')

        # Create 10 posts with author and tags
        for i in range(10):
            p = Post.objects.create(
                author=self.user,
                title=f'Post {i}',
                slug=f'post-{i}',
                body='Content of post',
                status='published'
            )
            p.tags.add(self.tag1, self.tag2)
            update_single_post_stats(p)

    def test_post_list_query_count_is_constant(self):
        """Verify PostListView does not suffer from N+1 queries when loading posts, authors, tags."""
        with self.assertNumQueries(4):
            # 1: Pagination COUNT query
            # 2: Top trending query with select_related post and author
            # 3: Posts query with author select_related + likes/comments count annotations
            # 4: Tags prefetch for the current page posts
            response = self.client.get(reverse('post_list'))
            self.assertEqual(response.status_code, 200)
