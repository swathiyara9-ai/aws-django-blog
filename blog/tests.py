from io import BytesIO
from unittest.mock import patch, PropertyMock, MagicMock
from PIL import Image
from django.conf import settings
from django.test import TestCase, override_settings
from django.core.files.storage import StorageHandler, storages, FileSystemStorage
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from storages.backends.s3 import S3Storage
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

    def test_health_check_endpoint(self):
        """ALB health check endpoint returns HTTP 200 OK without requiring authentication."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('app'), 'aws-django-blog')


class MediaStorageConfigurationTests(TestCase):
    def test_default_local_storage_when_bucket_unset(self):
        """When AWS_STORAGE_BUCKET_NAME is unset, user media uses local FileSystemStorage."""
        self.assertIsNone(getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None))
        default_storage = storages['default']
        self.assertIsInstance(default_storage, FileSystemStorage)
        # Static files must remain on WhiteNoise
        self.assertEqual(
            settings.STORAGES['staticfiles']['BACKEND'],
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
        )

    def test_s3_storage_configuration_when_bucket_set(self):
        """When AWS_STORAGE_BUCKET_NAME is configured, S3Storage backend is initialized with s3v4 and querystring auth."""
        s3_storages = {
            'default': {
                'BACKEND': 'storages.backends.s3.S3Storage',
                'OPTIONS': {
                    'bucket_name': 'my-production-media-bucket',
                    'region_name': 'ap-southeast-2',
                    'endpoint_url': 'https://s3.ap-southeast-2.amazonaws.com',
                    'addressing_style': 'virtual',
                    'signature_version': 's3v4',
                    'file_overwrite': False,
                    'querystring_auth': True,
                },
            },
            'staticfiles': {
                'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
            },
        }
        with override_settings(
            AWS_STORAGE_BUCKET_NAME='my-production-media-bucket',
            AWS_S3_REGION_NAME='ap-southeast-2',
            AWS_S3_SIGNATURE_VERSION='s3v4',
            AWS_S3_FILE_OVERWRITE=False,
            AWS_QUERYSTRING_AUTH=True,
            STORAGES=s3_storages
        ):
            handler = StorageHandler()
            storage = handler['default']
            self.assertIsInstance(storage, S3Storage)
            self.assertEqual(storage.bucket_name, 'my-production-media-bucket')
            self.assertEqual(storage.region_name, 'ap-southeast-2')
            self.assertEqual(storage.endpoint_url, 'https://s3.ap-southeast-2.amazonaws.com')
            self.assertEqual(storage.addressing_style, 'virtual')
            self.assertEqual(storage.signature_version, 's3v4')
            self.assertFalse(storage.file_overwrite)
            self.assertTrue(storage.querystring_auth)

    def test_s3_presigned_url_generation_without_aws_network_call(self):
        """S3Storage produces signed URLs using client presigning without calling live AWS."""
        storage = S3Storage(
            bucket_name='my-production-media-bucket',
            region_name='ap-southeast-2',
            signature_version='s3v4',
            file_overwrite=False,
            querystring_auth=True
        )
        mock_conn = MagicMock()
        mock_conn.meta.client.generate_presigned_url.return_value = (
            'https://my-production-media-bucket.s3.ap-southeast-2.amazonaws.com/uploads/photo.jpg'
            '?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=mockedsig123'
        )
        with patch.object(S3Storage, 'connection', new_callable=PropertyMock, return_value=mock_conn):
            url = storage.url('uploads/photo.jpg')
            self.assertTrue(url.startswith('https://my-production-media-bucket.s3.ap-southeast-2.amazonaws.com/'))
            self.assertIn('X-Amz-Signature=mockedsig123', url)
            mock_conn.meta.client.generate_presigned_url.assert_called_once()

    def test_s3_presigned_url_host_contains_region_without_network_call(self):
        """S3Storage generates virtual-hosted URL containing the regional endpoint without calling AWS."""
        storage = S3Storage(
            access_key='dummy-key',
            secret_key='dummy-secret',
            bucket_name='aws-django-blog-media-20261119',
            region_name='ap-southeast-2',
            endpoint_url='https://s3.ap-southeast-2.amazonaws.com',
            addressing_style='virtual',
            signature_version='s3v4',
            file_overwrite=False,
            querystring_auth=True
        )
        with patch('socket.socket') as mock_socket:
            url = storage.url('uploads/photo.jpg')
            # Verify host contains the regional endpoint and bucket name
            self.assertIn('aws-django-blog-media-20261119.s3.ap-southeast-2.amazonaws.com', url)
            self.assertIn('ap-southeast-2', url)
            self.assertIn('X-Amz-Signature=', url)
            # Guarantee no network socket was created or called
            self.assertFalse(mock_socket.called)


class FrontendRestructureAndFeedAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='password123')
        self.tag = Tag.objects.create(name='cloud')
        self.post = Post.objects.create(
            author=self.user,
            title='Understanding Cloud Architecture',
            slug='understanding-cloud-architecture',
            body='Comprehensive guide to cloud systems with ALB, EC2, and RDS.',
            summary='Cloud architecture overview.',
            status='published'
        )
        self.post.tags.add(self.tag)

    def test_post_feed_api_returns_json_and_dimensions(self):
        """Infinite scroll feed endpoint /posts/feed/ returns paginated JSON batch."""
        response = self.client.get(reverse('post_feed_api') + '?page=1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('posts', data)
        self.assertIn('has_next', data)
        self.assertEqual(len(data['posts']), 1)
        first_post = data['posts'][0]
        self.assertEqual(first_post['id'], self.post.id)
        self.assertEqual(first_post['title'], 'Understanding Cloud Architecture')
        self.assertIn('image_width', first_post)
        self.assertIn('image_height', first_post)
        self.assertIn('likes_count', first_post)
        self.assertIn('comments_count', first_post)

    def test_search_view_matches_title_and_body(self):
        """Global search returns matching posts in masonry card view."""
        response = self.client.get(reverse('search') + '?q=Architecture')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Understanding Cloud Architecture')
        self.assertTemplateUsed(response, 'blog/search_results.html')

    def test_trending_page_view(self):
        """Dedicated trending analytics page renders successfully."""
        response = self.client.get(reverse('trending_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/trending.html')
        self.assertContains(response, 'Trending Leaderboard')
        self.assertContains(response, 'Ranking Formula')

    def test_cloud_activity_page_view(self):
        """Dedicated cloud activity telemetry page renders successfully."""
        response = self.client.get(reverse('cloud_activity_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/cloud_activity.html')
        self.assertContains(response, 'Live Cloud Activity')

    def test_architecture_page_view(self):
        """Dedicated architecture overview page renders successfully."""
        response = self.client.get(reverse('architecture_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/architecture.html')
        self.assertContains(response, 'AWS Cloud Architecture')

    def test_ai_insights_page_view(self):
        """Dedicated AI insights telemetry page renders successfully."""
        response = self.client.get(reverse('ai_insights_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/ai_insights.html')
        self.assertContains(response, 'Amazon Bedrock AI Insights')

    def test_post_image_dimensions_saved_via_pillow(self):
        """Saving a post with an image computes image_width and image_height automatically."""
        test_img = get_test_image()
        img_post = Post.objects.create(
            author=self.user,
            title='Image Post',
            slug='image-post',
            body='Content with image',
            image=test_img,
            status='published'
        )
        self.assertEqual(img_post.image_width, 100)
        self.assertEqual(img_post.image_height, 100)

    def test_settings_view_requires_login(self):
        """Anonymous user is redirected to login when visiting settings."""
        response = self.client.get(reverse('user_settings'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_settings_view_renders_profile_for_authenticated_user(self):
        """Authenticated user sees their username, email, and preferences on settings page."""
        self.client.login(username='carol', password='password123')
        response = self.client.get(reverse('user_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'carol')
        self.assertContains(response, 'Interface Theme')
        self.assertContains(response, 'Cloud Status Strip')

    def test_post_detail_renders_reading_time_and_back_link(self):
        """Post detail renders the 2-column layout with reading time and single back button arrow."""
        response = self.client.get(reverse('post_detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to all posts')
        self.assertContains(response, 'bi-arrow-left')
        self.assertNotContains(response, '&larr;')
        self.assertContains(response, 'min read')
        self.assertEqual(response.context['reading_time'], 1)

    def test_theme_preload_and_css_variables_present(self):
        """Base template executes theme preload script in <head> and provides semantic theme variables."""
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("localStorage.getItem('appTheme')", content)
        self.assertIn('data-bs-theme', content)
        self.assertIn('--text-secondary', content)
        self.assertIn('--surface', content)


    def test_post_detail_comments_ordered_newest_first(self):
        """Comments on post detail are ordered newest first."""
        Comment.objects.create(post=self.post, author=self.user, body='First comment', is_approved=True)
        Comment.objects.create(post=self.post, author=self.user, body='Second comment', is_approved=True)
        response = self.client.get(reverse('post_detail', kwargs={'slug': self.post.slug}))
        comments = list(response.context['comments'])
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].body, 'Second comment')
        self.assertEqual(comments[1].body, 'First comment')


class HashtagInputAndValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='password123')
        self.existing_tag = Tag.objects.create(name='python')

    def test_create_post_creates_new_tag_and_reuses_existing(self):
        """PostForm creates new Tag instances and reuses existing ones via get_or_create."""
        self.client.login(username='dave', password='password123')
        post_data = {
            'title': 'Hashtag Test Post',
            'body': 'Testing new and existing hashtag chips in post form.',
            'summary': 'Summary',
            'tags': 'python, django, aws_cloud',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check post created
        post = Post.objects.get(title='Hashtag Test Post')
        tag_names = set(post.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, {'python', 'django', 'aws_cloud'})

        # Verify existing tag was reused and not duplicated
        self.assertEqual(Tag.objects.filter(name='python').count(), 1)
        self.assertTrue(Tag.objects.filter(name='django').exists())
        self.assertTrue(Tag.objects.filter(name='aws_cloud').exists())

    def test_hashtag_normalisation_and_deduplication(self):
        """Hashtags strip '#', lowercase, trim whitespace, and remove duplicates."""
        self.client.login(username='dave', password='password123')
        post_data = {
            'title': 'Normalisation Post',
            'body': 'Content testing hashtag normalisation.',
            'tags': '#Django,  #PYTHON , python,  #AWS_Cloud ',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        post = Post.objects.get(title='Normalisation Post')
        tag_names = list(post.tags.values_list('name', flat=True))
        self.assertIn('django', tag_names)
        self.assertIn('python', tag_names)
        self.assertIn('aws_cloud', tag_names)
        # Verify deduplication (python was submitted twice with different casing/spacing)
        self.assertEqual(len(tag_names), 3)

    def test_hashtag_limit_to_10_tags_enforced(self):
        """Submitting more than 10 tags returns a validation error."""
        self.client.login(username='dave', password='password123')
        post_data = {
            'title': 'Too Many Tags Post',
            'body': 'Content testing tag limit.',
            'tags': 'tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10, tag11',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'tags', 'A post can have at most 10 tags.')
        # Post was not created
        self.assertFalse(Post.objects.filter(title='Too Many Tags Post').exists())

    def test_hashtag_invalid_character_validation(self):
        """Hashtags with special characters (other than underscore) raise validation error."""
        self.client.login(username='dave', password='password123')
        post_data = {
            'title': 'Invalid Tag Post',
            'body': 'Content testing invalid tag characters.',
            'tags': 'valid_tag, invalid$tag',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'tags',
            "Invalid tag '#invalid$tag'. Tags can only contain letters, numbers, and underscores."
        )

    def test_tag_autocomplete_api(self):
        """Autocomplete API returns matching tags for query parameter 'q'."""
        Tag.objects.create(name='docker')
        Tag.objects.create(name='documentation')

        # Match 'doc'
        response = self.client.get(reverse('tag_autocomplete_api') + '?q=doc')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('tags', data)
        self.assertIn('docker', data['tags'])
        self.assertIn('documentation', data['tags'])
        self.assertNotIn('python', data['tags'])

        # Works with leading '#'
        response = self.client.get(reverse('tag_autocomplete_api') + '?q=%23py')
        self.assertEqual(response.status_code, 200)
        self.assertIn('python', response.json()['tags'])

    def test_edit_post_prefills_existing_tags(self):
        """Edit post view pre-fills existing tags in form initial data."""
        self.client.login(username='dave', password='password123')
        post = Post.objects.create(
            author=self.user,
            title='Post to Edit',
            slug='post-to-edit',
            body='Body of post to edit',
            status='published'
        )
        t1 = Tag.objects.create(name='tagone')
        t2 = Tag.objects.create(name='tagtwo')
        post.tags.add(t1, t2)

        response = self.client.get(reverse('post_update', kwargs={'slug': post.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tagone')
        self.assertContains(response, 'tagtwo')

    def test_form_validation_error_keeps_typed_tags(self):
        """When another form field has an error, submitted tags are preserved in the form."""
        self.client.login(username='dave', password='password123')
        # Missing required title
        post_data = {
            'title': '',
            'body': 'Body text with enough length to be valid',
            'tags': 'django, python',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="django, python"')


class FeedNavigationAndNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        # Create 20 published posts for 16-item batching
        for i in range(1, 21):
            Post.objects.create(
                author=self.user,
                title=f'Server Post {i}',
                slug=f'server-post-{i}',
                body=f'Body content for test post number {i}.',
                status='published'
            )

    def test_home_page_html_contains_cards_without_javascript(self):
        """The home page HTML always renders post cards directly on the server without needing JS."""
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        # Server HTML contains cards
        self.assertContains(response, 'post-feed-card')
        # First batch (16 posts) are rendered directly in the HTML
        self.assertEqual(len(response.context['posts']), 16)
        self.assertContains(response, 'id="scroll-sentinel"')
        self.assertContains(response, 'id="masonry-feed"')

    def test_feed_endpoint_returns_next_batch_with_cache_control_no_store(self):
        """JSON feed endpoint returns page 2 with Cache-Control: no-store."""
        response = self.client.get(reverse('post_feed_api') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers.get('Cache-Control', ''))
        data = response.json()
        self.assertIn('posts', data)
        self.assertEqual(len(data['posts']), 4)  # 20 total - 16 on page 1 = 4 on page 2
        self.assertFalse(data['has_next'])

    def test_create_post_emits_single_consolidated_cloud_message(self):
        """Creating a post emits exactly ONE flash message containing cloud timings and link."""
        self.client.login(username='tester', password='password123')
        post_data = {
            'title': 'New Cloud Profiled Post',
            'body': 'Content for the profiled post with cloud timings.',
            'status': 'published'
        }
        response = self.client.post(reverse('post_create'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Verify exactly 1 message in messages framework
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        toast_text = str(messages_list[0])
        self.assertIn('Post saved', toast_text)
        self.assertIn('View in Cloud Activity', toast_text)

    def test_favicon_endpoint_returns_svg(self):
        """Favicon route returns 200 OK with SVG content type."""
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')






