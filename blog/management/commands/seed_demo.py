import hashlib
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from blog.models import Post, Tag, Comment, Like
from analytics.models import PostView
from analytics.services import update_single_post_stats


class Command(BaseCommand):
    help = "Seeds 12 realistic demo users, published posts, tags, comments, and likes. Requires --yes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirm execution. Required to prevent accidental execution in production.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError(
                "Confirmation required: run with '--yes' to confirm seeding demo data. "
                "Example: python manage.py seed_demo --yes"
            )

        self.stdout.write(self.style.WARNING("Starting demo data seeding..."))

        # 1. Create or get Tags
        tag_names = [
            'aws', 'django', 'python', 'bedrock', 'ec2', 's3',
            'postgresql', 'docker', 'terraform', 'security', 'devops', 'cloud'
        ]
        tag_objs = {}
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objs[name] = tag

        # 2. Create 12 Demo Users
        user_specs = [
            ('swathi_it', 'Swathi', 'R', 'swathi@example.com'),
            ('alex_cloud', 'Alex', 'Chen', 'alex@example.com'),
            ('priya_dev', 'Priya', 'Sharma', 'priya@example.com'),
            ('marcus_aws', 'Marcus', 'Vance', 'marcus@example.com'),
            ('elena_sre', 'Elena', 'Rostova', 'elena@example.com'),
            ('david_data', 'David', 'Miller', 'david@example.com'),
            ('aisha_sec', 'Aisha', 'Khan', 'aisha@example.com'),
            ('raj_ops', 'Raj', 'Patel', 'raj@example.com'),
            ('liam_infra', 'Liam', 'OConnor', 'liam@example.com'),
            ('zara_arch', 'Zara', 'Nasser', 'zara@example.com'),
            ('hannah_ai', 'Hannah', 'Schmidt', 'hannah@example.com'),
            ('carlos_sys', 'Carlos', 'Mendoza', 'carlos@example.com'),
        ]
        created_users = []
        for username, first, last, email in user_specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last, 'email': email}
            )
            if created:
                user.set_password('demoPassword123!')
                user.save()
            created_users.append(user)

        # 3. Define 12 Realistic Engineering Articles
        articles = [
            {
                'title': 'Building a Production-Ready Django 5.2 Application on AWS EC2',
                'summary': 'A practical walkthrough of deploying Django with Gunicorn, Nginx, and systemd on Amazon Linux 2023 with zero downtime.',
                'body': (
                    "Deploying Django in production requires moving beyond manage.py runserver. "
                    "In this guide, we configure Gunicorn as a WSGI server managed by systemd, "
                    "use Nginx as a reverse proxy for SSL termination and static file handling, "
                    "and connect securely to an Amazon RDS PostgreSQL database residing in private subnets. "
                    "We also review environment variable isolation and graceful worker restarts."
                ),
                'tags': ['aws', 'django', 'ec2', 'devops'],
                'author_idx': 0,
            },
            {
                'title': 'Why S3 Presigned URLs Beat Direct File Uploads Through Application Servers',
                'summary': 'How offloading binary file uploads to Amazon S3 prevents application worker starvation and scales gracefully.',
                'body': (
                    "When users upload high-resolution images or videos directly to a web application server, "
                    "the server worker thread remains blocked throughout the entire upload duration. "
                    "With S3 presigned URLs, Django authenticates the request and issues a cryptographically "
                    "signed PUT URL. The client uploads directly to S3, bypassing our application backend "
                    "and reducing EC2 bandwidth pressure to near zero."
                ),
                'tags': ['s3', 'aws', 'python', 'security'],
                'author_idx': 1,
            },
            {
                'title': 'Implementing Amazon Bedrock Nova Lite with Resilient Fallback AI Strategies',
                'summary': 'Integrating Amazon Nova Lite via the Converse API with offline mock generators for reliable user suggestions.',
                'body': (
                    "Generative AI enhances editorial workflows, but external APIs can be throttled or unavailable. "
                    "In our architecture, we target Amazon Nova Lite (amazon.nova-lite-v1:0) in the Sydney region. "
                    "When credentials are unset or during local testing, an offline heuristic generator transparently "
                    "synthesizes title variations, hashtag extractions, and summaries with zero latency impact."
                ),
                'tags': ['bedrock', 'python', 'cloud'],
                'author_idx': 2,
            },
            {
                'title': 'Mastering PostgreSQL Connection Pooling with Amazon RDS',
                'summary': 'Diagnosing connection spikes and optimizing database throughput on AWS RDS with Django persistent connections.',
                'body': (
                    "Opening a new TCP and SSL connection to PostgreSQL on every HTTP request introduces significant latency. "
                    "By leveraging Django's CONN_MAX_AGE and deploying RDS Proxy in high-concurrency environments, "
                    "we reuse database connections across requests, dramatically improving response times and preventing "
                    "connection pool exhaustion during traffic surges."
                ),
                'tags': ['postgresql', 'aws', 'django'],
                'author_idx': 3,
            },
            {
                'title': 'Eliminating Layout Shift in Responsive Masonry Feeds with Pillow',
                'summary': 'Calculating aspect ratios server-side to guarantee stable, jump-free infinite scrolling across all devices.',
                'body': (
                    "Cumulative Layout Shift (CLS) degrades user experience when images load asynchronously into the DOM. "
                    "By reading image dimensions with Pillow upon post creation and persisting image_width and image_height, "
                    "the HTML template specifies CSS aspect-ratio. The browser calculates exact layout boundaries before image bytes "
                    "arrive, delivering seamless 4-column masonry scrolling."
                ),
                'tags': ['django', 'python'],
                'author_idx': 4,
            },
            {
                'title': 'Designing Least-Privilege IAM Roles for EC2 Application Workloads',
                'summary': 'Why hard-coded AWS credentials are a security risk and how IAM instance profiles solve credential rotation.',
                'body': (
                    "Hard-coding AWS access keys inside .env files or git repositories is a leading cause of cloud breaches. "
                    "By attaching an IAM Instance Profile to our EC2 instances, the AWS SDK and boto3 automatically retrieve "
                    "temporary credentials from the EC2 Instance Metadata Service (IMDSv2). Policies are scoped strictly to "
                    "the target S3 bucket and Bedrock foundation model."
                ),
                'tags': ['security', 'aws', 'cloud'],
                'author_idx': 5,
            },
            {
                'title': 'Real-Time Trending Formulas with Exponential Time Decay',
                'summary': 'Building Hacker News-style ranking algorithms that balance engagement volume against post age.',
                'body': (
                    "A naive leaderboard sorted solely by total likes results in older posts permanently dominating the homepage. "
                    "We implement a gravity-based time-decay formula: Score = (Views*1 + Comments*3 + Likes*5) / (Age_Hours + 2)^1.5. "
                    "This ensures fresh, engaging discussions naturally rise to the top while older posts gradually give way."
                ),
                'tags': ['python', 'django'],
                'author_idx': 6,
            },
            {
                'title': 'Demystifying AWS IMDSv2 and Protecting Against SSRF in Production',
                'summary': 'Understanding session-oriented token requests in Instance Metadata Service Version 2.',
                'body': (
                    "IMDSv1 allowed arbitrary HTTP GET requests to 169.254.169.254, making it vulnerable to Server-Side Request Forgery. "
                    "IMDSv2 requires a PUT request with an X-aws-ec2-metadata-token-ttl-seconds header to obtain a session token, "
                    "which must then be included in subsequent metadata requests. This prevents reverse proxies and open redirects "
                    "from exfiltrating IAM credentials."
                ),
                'tags': ['security', 'aws', 'ec2'],
                'author_idx': 7,
            },
            {
                'title': 'Zero-Downtime Deployments with Gunicorn and Nginx Reverse Proxies',
                'summary': 'Configuring UNIX domain sockets, master worker reloads, and keepalive timeouts for seamless application updates.',
                'body': (
                    "When updating application code on EC2, restarting the web server can briefly drop in-flight requests. "
                    "By utilizing Gunicorn master-worker architecture with UNIX sockets and issuing HUP signals (systemctl reload), "
                    "the master process spawns new workers with updated code and gracefully phases out old workers only after "
                    "they complete current requests."
                ),
                'tags': ['devops', 'django', 'ec2'],
                'author_idx': 8,
            },
            {
                'title': 'Building Asymmetric Sticky Reading Layouts with Plain Bootstrap 5',
                'summary': 'Structuring 55/45 two-column article viewports with native sticky scrolling and zero external libraries.',
                'body': (
                    "Modern media-rich articles benefit from an asymmetric desktop layout where visual media stays pinned on the left "
                    "while long-form content, comments, and interactions scroll on the right. Using position: sticky with top offsets "
                    "and responsive flexbox stacking on mobile achieves a polished reader experience without adding heavy frontend frameworks."
                ),
                'tags': ['django'],
                'author_idx': 9,
            },
            {
                'title': 'Multi-Service Latency Tracing Across AWS Cloud Infrastructure',
                'summary': 'Building transparent in-app telemetry tracking real step-by-step latency across Django, RDS, S3, and Bedrock.',
                'body': (
                    "Cloud visibility should not be locked inside complex external monitoring dashboards. Our CloudTracker "
                    "measures elapsed time using time.perf_counter() for each step: ORM database persistence, S3 object upload, "
                    "and AI inference. Metrics are saved to ActivityEvent models and surfaced via real-time toasts and live pipeline streams."
                ),
                'tags': ['cloud', 'aws', 'django'],
                'author_idx': 10,
            },
            {
                'title': 'A Student Guide to Preparing for AWS Cloud Architecture Interviews',
                'summary': 'Key lessons learned while building and deploying a production Django application on AWS for undergraduate viva and interviews.',
                'body': (
                    "Building a real cloud project provides insights no theoretical textbook can match. From understanding "
                    "why public subnets are reserved for load balancers while database instances live in private subnets, to managing "
                    "CORS, CSRF, and IAM role authentication, this retrospective shares the most common architectural questions "
                    "asked by mentors and engineering interviewers."
                ),
                'tags': ['aws', 'cloud', 'security', 'devops'],
                'author_idx': 11,
            },
        ]

        # 4. Create Posts
        created_posts = []
        for i, art in enumerate(articles):
            author = created_users[art['author_idx']]
            base_slug = slugify(art['title'])
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            post, created = Post.objects.get_or_create(
                slug=slug,
                defaults={
                    'author': author,
                    'title': art['title'],
                    'summary': art['summary'],
                    'body': art['body'],
                    'status': 'published',
                }
            )
            # Add tags
            for tname in art['tags']:
                post.tags.add(tag_objs[tname])

            created_posts.append(post)

        # 5. Create Realistic Comments
        comment_samples = [
            "Great explanation! The distinction between public and private subnets is super clear.",
            "Really enjoyed the breakdown of time decay. Much better than static upvote lists.",
            "The CloudTracker telemetry feature is fantastic for visualizing real latencies.",
            "Very helpful walkthrough. Testing this setup on our staging EC2 instance.",
            "The Pillow aspect-ratio technique completely eliminated layout shift on mobile for me.",
            "Clean architecture. Appreciate the focus on IAM roles rather than hardcoding credentials.",
        ]
        total_comments = 0
        for post in created_posts:
            # 1 to 3 comments per post from other users
            commenters = [u for u in created_users if u != post.author]
            selected_commenters = random.sample(commenters, k=min(3, len(commenters)))
            for commenter in selected_commenters:
                body = random.choice(comment_samples)
                Comment.objects.get_or_create(
                    post=post,
                    author=commenter,
                    body=body,
                    defaults={'is_approved': True}
                )
                total_comments += 1

        # 6. Create Realistic Likes
        total_likes = 0
        for post in created_posts:
            likers = [u for u in created_users if u != post.author]
            # 2 to 5 likes per post
            k_likes = random.randint(2, min(5, len(likers)))
            for user in random.sample(likers, k=k_likes):
                Like.objects.get_or_create(post=post, user=user)
                total_likes += 1

        # 7. Record Simulated Views & Update Trending Scores
        for post in created_posts:
            # Simulate 5-15 views
            num_views = random.randint(5, 15)
            for v in range(num_views):
                visitor_hash = hashlib.sha256(f"seed-visitor-{post.id}-{v}".encode()).hexdigest()
                PostView.objects.create(
                    post=post,
                    visitor_hash=visitor_hash,
                )
            # Recalculate stats & score
            update_single_post_stats(post)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded demo database!\n"
            f"- Users: {len(created_users)}\n"
            f"- Posts: {len(created_posts)}\n"
            f"- Tags: {len(tag_objs)}\n"
            f"- Comments: {total_comments}\n"
            f"- Likes: {total_likes}\n"
            f"- Trending scores initialized."
        ))
