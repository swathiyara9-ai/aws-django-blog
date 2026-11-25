# Build Plan and Status

Rule: work one phase at a time. Tick boxes only after testing. After each phase, update `LEARNING_LOG.md`.

## Open decisions
- [ ] Infrastructure as code tool: Terraform or CloudFormation
- [ ] Database engine on RDS: MySQL or PostgreSQL
- [x] AWS region: `ap-southeast-2` (Sydney)
- [x] Bedrock model to use: Amazon Nova Lite (`amazon.nova-lite-v1:0`, IAM ARN: `arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0`)

## Phase 0 — Local setup
- [ ] Python 3.10+ installed, virtual environment created
- [ ] Django installed, project `config` and app `blog` created
- [ ] `python manage.py runserver` shows the Django welcome page
- [ ] Git repository initialised, `.gitignore` added, first commit
Done when: the welcome page opens at http://127.0.0.1:8000

## Phase 1 — Models and admin
- [x] Models: Tag, Post, Comment, Like (see `DATABASE.md`)
- [x] Migrations created and applied
- [x] Models registered in admin; superuser created
Done when: you can create a Post with tags from the admin panel.

## Phase 2 — Authentication and post CRUD
- [x] Base template with Bootstrap and navbar
- [x] Register, login, logout pages
- [x] Post list (paginated) and detail pages
- [x] Create, edit, delete post (author only)
Done when: a new user can register, write, edit and delete their own post, and cannot edit others' posts.

## Phase 3 — Comments, likes, images
- [x] Comment form on post detail
- [x] Like / unlike button
- [x] Image upload (local `media/`)
- [x] Tag filter page
Done when: images show on posts and comments and likes work.

## Phase 4 — Trending analytics (stage 1, local)
- [x] `analytics` app with PostView and PostStats
- [x] Record view on post detail (with simple de-duplication)
- [x] Score calculation service and management command `compute_trending`
- [x] Trending section on home page
Done when: opening, liking and commenting on posts changes the Trending order after running the command.

## Phase 5 — AI suggestions (Bedrock)
- [x] `ai_assist` app with `services.py`
- [ ] AWS credentials configured locally; Bedrock model access confirmed
- [x] Endpoint returns JSON {titles, hashtags, summary}
- [x] "Suggest" button in editor; author can apply or ignore each suggestion
- [x] Error handling, input length limit, simple rate limit
Done when: clicking Suggest fills the editor options, and the editor still works if Bedrock is unreachable.

## Phase 6 — Production readiness
- [x] Settings split by environment variables (`DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, DB, bucket, `BEDROCK_MODEL_ID`)
- [x] Gunicorn, WhiteNoise or S3 for static files
- [x] `requirements.txt` pinned; `collectstatic` works
- [x] Health check URL `/health/`
Done when: the app runs locally in production-like mode with `DEBUG=False`.

## Phase 7 — AWS networking and safety
- [ ] AWS Budget alert created
- [ ] VPC, public and private subnets in 2 AZs, internet gateway, route tables
- [ ] Security groups: ALB, EC2, RDS
- [ ] S3 VPC gateway endpoint
Done when: network diagram matches `ARCHITECTURE.md`.

## Phase 8 — RDS and S3 (Storage & Cloud Telemetry)
- [ ] RDS instance in private subnets
- [ ] Django connects to RDS (from a test EC2 instance)
- [x] django-storages S3 media backend configured (fallback to local media/ when bucket unset, s3v4 signed URLs, no hardcoded keys)
- [ ] S3 media bucket created with Block Public Access ON (AWS console/Terraform)
- [ ] IAM role for EC2 (least privilege)
- [x] CloudLog telemetry backend: ActivityEvent model & real-time operation timing (Django/Gunicorn, DB, S3, Bedrock/Mock AI)
- [x] Real-time trending score recalculation on user activity with 30-second caching & rank change tracking
- [x] Public JSON APIs: /api/cloud-activity/, /api/trending/, /api/cloud-status/ (IMDSv2), /api/ai-insights/
- [x] Query optimization on post lists (select_related + prefetch_related + annotations, 0 N+1 queries)
- [x] Frontend restructure: Left sidebar icon rail (~72px, expands on hover/toggle; bottom nav on mobile)
- [x] Top bar with global search box and slim status strip ("Health: 200 OK", region, DB, storage, AI mode)
- [x] Home masonry feed: 3 column containers (2 tablet, 1 mobile), append to shortest column, image-first rounded cards, color blocks for non-image posts, top 3 flame badges
- [x] Endless vertical scroll with IntersectionObserver, 12-item batching, de-duplication, skeleton loader, "all caught up" state, noscript fallback
- [x] Prevent layout jumps: `image_width` and `image_height` on `Post` populated on save via Pillow, `aspect-ratio` on `<img>`, lazy loading and async decoding
- [x] Dedicated Trending page with hero top 3 large cards, ranks 4-10, score breakdown bars, rank changes, formula explanation, 15s auto-refresh
- [x] Full telemetry pages for Cloud Activity (pipeline view with real ms), Architecture overview, and AI Insights
- [x] Improved AI mock suggestions: 4 distinct title styles (statement, question, headline, story), stop-words filtering, first-sentence summary
- [x] Sidebar polish: single centered '+' icon on collapsed rail, 'Create Post' on expand, overlay with high z-index and shadow (no layout shift)
- [x] Pinned sidebar bottom items: Settings (gear icon) and Logout (POST form with CSRF); top bar displays username
- [x] Settings page (login required): Profile info, Django PasswordChangeView, localStorage theme switch (light/dark), and status strip visibility checkbox
- [x] Post Detail polish: 55% / 45% two-column sticky layout on desktop (stacked on mobile), object-fit contain image with fullscreen lightbox modal, exact right-column element hierarchy (title, author/date, details row, tags, body, like/edit/delete, newest comments first, comment form), and browser history back button
- [x] Real cloud timing toasts for post create, edit, and delete operations
- [x] Bugfix: Single arrow on "Back to all posts" navigation (removed duplicate entity)
- [x] Bugfix: Comprehensive WCAG AA dark mode system with CSS variables, zero-flash head preload, and instant theme switching across all pages
- [x] Hashtag chip input control: Interactive text input (Enter/comma/space to add chip, 'x' remove, backspace delete), live autocomplete API (`/api/tags/?q=`), AI suggestion chip synchronization (highlight and toggle)
- [x] Hashtag backend normalisation: lowercase, strip '#'/spaces, regex validation (`^[a-z0-9_]+$`), max 50 chars, max 10 tags limit, deduplication, auto `get_or_create`, and edit-mode pre-filling
- [x] Bugfix: Feed back-navigation restoration (relative `{% url 'post_list' %}` URL, persistent server-rendered HTML batch 1, bfcache `pageshow` handling, observer re-attachment, and sequential batch restoration)
- [x] Bugfix: Consolidated cloud timing notifications into single toast container (de-duplicated via sessionStorage, 4s auto-hide, no double messages or alert banner repetition)
- [x] Mobile navigation polish: added "More" item with offcanvas bottom sheet for Architecture, AI Insights, and Settings
- [x] Favicon route (`/favicon.ico`) and SVG link to eliminate console 404s
- [x] Feed endpoint cache prevention (`Cache-Control: no-store`) with error state and interactive retry button
- [x] 4-column desktop masonry layout (4 cols >= 1200px, 3 cols from 900px, 2 cols from 576px, 1 col below), single-config breakpoint rebalancer, 16-post batching (server & API), narrower cards (compact padding, 2-line title ellipsis, max 2 tags, single-line author/counts)
- [x] Seed demo management command (`python manage.py seed_demo --yes`) creating 12 realistic users, posts, tags, comments, likes, and trending scores with `--yes` safety gate
- [x] Final submission wrap-up: Comprehensive README rewrite with honest status table, architecture diagram, settings reference, and local run guide
- [x] Documentation suite: Real-state ARCHITECTURE.md, in-app Architecture template, DEPLOYMENT.md runbook, TESTING.md manual checklist, and VIVA.md (15 Q&As)
- [x] Security audit & deployment validation: Repo scanned for secrets (0 leaked keys), .env.example updated with placeholders, .gitignore verified, and python manage.py check --deploy verified clean
Done when: posts and images save to RDS and S3 from an EC2 test instance, cloud activity telemetry is observable, and full submission documentation is verified.

## Phase 9 — EC2, ALB and Auto Scaling
- [ ] Launch template with user-data script that installs and starts the app
- [ ] Target group and ALB with health check
- [ ] Auto Scaling group (min 2, max 3-4) with CPU target policy
- [ ] Test: terminate one instance, site stays up; load test triggers scale-out
Done when: the ALB DNS name serves the blog and survives an instance failure.

## Phase 10 — CloudFront and HTTPS
- [ ] ACM certificate (us-east-1 for CloudFront)
- [ ] CloudFront distribution in front of ALB, S3 origin for media
- [ ] Optional Route 53 domain
Done when: the site opens over HTTPS via CloudFront.

## Phase 11 — Lambda and serverless analytics (stage 2)
- [ ] S3-triggered Lambda (alt-text or thumbnail)
- [ ] API Gateway + Lambda + DynamoDB view counter
- [ ] EventBridge hourly Lambda computing trending scores
Done when: view counts come from DynamoDB and Trending reads from them.

## Phase 12 — Infrastructure as code
- [ ] Network, ALB, ASG, RDS, S3 defined in the chosen IaC tool
- [ ] Rebuild environment from code in a clean state
Done when: the stack can be created and destroyed from code.

## Phase 13 — CI/CD, monitoring, final docs
- [ ] GitHub Actions: tests on push; deploy step
- [ ] CloudWatch alarms (CPU, 5xx, DB connections) and dashboards
- [ ] README with architecture diagram and screenshots
- [ ] Demo script and viva Q&A prepared
Done when: a push triggers tests and deployment, and alarms are visible.

## Teardown checklist (run after demos)
- [ ] Scale Auto Scaling group to 0 or delete
- [ ] Delete ALB and target groups
- [ ] Stop or delete RDS (take snapshot if needed)
- [ ] Delete NAT Gateway and release Elastic IPs
- [ ] Empty and delete S3 buckets if not needed
- [ ] Delete CloudFront distribution
- [ ] Check the Billing dashboard the next day
