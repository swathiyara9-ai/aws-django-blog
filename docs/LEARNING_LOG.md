# Learning Log (interview and viva prep)

After every phase, add an entry. Keep answers in your own words.

## Template
### Phase N — Title (date)
**What I built:**
**New concepts:** (term — one-line meaning)
**Problems faced and fixes:**
**Likely questions and my answers:**
1. Q:
   A:
**Can I honestly put this on my resume?** yes / not yet (reason)

---

## Phase 0 — Local setup
**What I built:** Django project `config` and app `blog` running locally in a virtual environment.
**New concepts:**
- Virtual environment — private set of Python packages for one project.
- Django project vs app — project holds settings and routing; apps hold features.
- `manage.py` — command-line control panel for Django.
**Likely questions and my answers:**
1. Q: Why use a virtual environment?
   A: (write in your own words)


---

## Phase 1 — Models and admin (November 12, 2026)
**What I built:** Core database models (`Tag`, `Post`, `Comment`, `Like`) in Django ORM, created and applied migrations, and registered all models in the Django admin dashboard with search, filters, and auto-populated slugs.
**New concepts:**
- ORM (Object-Relational Mapping) — Translates Python model classes directly into database tables and SQL queries.
- Migration — A version-controlled Python script describing changes to database schema over time.
- ForeignKey — Creates a one-to-many relationship (e.g. one User has many Posts).
- ManyToManyField — Creates a many-to-many relationship using a bridge/junction table (e.g. Posts and Tags).
- UniqueConstraint — Enforces uniqueness at the database level across multiple columns (e.g. one Like per post per user).
- Django Admin — Built-in back-office UI for managing data models without writing custom admin views.
**Problems faced and fixes:**
- Need Pillow installed for `ImageField`: confirmed `pillow==12.2.0` is pinned in `requirements.txt`.
- Configured `MEDIA_URL` and `MEDIA_ROOT` in `settings.py` so uploaded images are stored neatly in `media/posts/`.
**Likely questions and my answers:**
1. Q: What is a migration and why shouldn't you edit the database schema directly?
   A: A migration is a version-controlled Python file that records changes made to models. Editing database tables directly bypasses version control, makes team collaboration and CI/CD impossible to reproduce, and can cause Django's model state and database schema to fall out of sync.
2. Q: What is the difference between ForeignKey and ManyToManyField in Django?
   A: A ForeignKey represents a one-to-many relationship (a Comment points to one Post, but a Post has many Comments). A ManyToManyField represents an N-to-N relationship (a Post can have multiple Tags, and a Tag can belong to multiple Posts) handled via a hidden junction table.
3. Q: How do you prevent a user from liking the same post multiple times?
   A: By defining a `UniqueConstraint(fields=['post', 'user'], name='unique_post_user_like')` in the `Like` model's `Meta` class, the database itself enforces that a given `(post, user)` pair can only exist once.
**Can I honestly put this on my resume?** Yes — Built relational data models in Django ORM with foreign keys, M2M relationships, and composite constraints, with a configured administrative backend.


---

## Phase 2 — Authentication and post CRUD (November 12, 2026)
**What I built:** User registration with automatic login, CSRF-protected authentication (login/logout), base Bootstrap 5 template with responsive navbar and dismissible alerts, full CRUD for posts via Class-Based Views (`ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`), slug collision handling, author authorization via mixins, draft isolation, and an 8-test automated suite.
**New concepts:**
- Class-Based Views (CBVs) — Object-oriented views (`ListView`, `CreateView`, etc.) that eliminate repetitive boilerplate for standard CRUD operations.
- Mixins — Composable classes (`LoginRequiredMixin`, `UserPassesTestMixin`) used to inject authentication and permission checks into views.
- CSRF Token — A cryptographic token included in state-changing requests (POST) to protect users from Cross-Site Request Forgery attacks.
- Template Inheritance — Reusable layout architecture where pages extend a parent template (`base.html`) and override specific content blocks.
- Authentication vs Authorization — Authentication verifies user identity (logging in); Authorization restricts actions based on permissions (author-only editing).
- Slug — A URL-friendly string derived from a title, providing human-readable, SEO-optimized web addresses.
**Problems faced and fixes:**
- Django 5 enforces POST requests for logout to prevent CSRF attacks: replaced plain link with a CSRF-protected form submit button in the navbar.
- Draft posts needed to remain visible to the author for previewing while remaining invisible to the public: filtered `PostDetailView` queryset with `Q(status='published') | Q(author=request.user)`.
**Likely questions and my answers:**
1. Q: What is the difference between Authentication and Authorization, and how did you implement them?
   A: Authentication verifies *who the user is* (handled by Django's `auth` views and `UserCreationForm`). Authorization determines *what the user is permitted to do* (enforced via `UserPassesTestMixin` on `PostUpdateView` and `PostDeleteView` to restrict edits and deletions strictly to the post's author, returning HTTP 403 to unauthorized users).
2. Q: Why use Class-Based Views (CBVs) instead of function-based views (FBVs)?
   A: CBVs encapsulate standard patterns like listing, pagination, form validation, and deletion into reusable classes. They allow clean code reuse through inheritance and mixins without rewriting boilerplate logic, while still offering granular hooks like `form_valid()` and `get_queryset()` when customization is needed.
3. Q: Why does Django 5 require logout to be a POST request instead of a simple GET link?
   A: Using GET requests for state-changing operations like logout makes the application vulnerable to Cross-Site Request Forgery (CSRF). A malicious website could trick a user's browser into visiting `/logout/` via an image tag or hidden link. Enforcing a POST request with a CSRF token ensures logouts are deliberate and originating from our trusted site.
**Can I honestly put this on my resume?** Yes — Implemented authentication, role-based authorization, and complete CRUD workflows using Django Class-Based Views, secured with CSRF protection and covered by unit tests.


---

## Phase 3 — Comments, likes, images, tags (November 12, 2026)
**What I built:** Image cover uploads with media file serving in development, interactive like/unlike button with like counts and unique constraint deduplication, comment submission form and comments feed displayed newest-first, and a dedicated tag filter feed (`/tag/<tag_name>/`) with active hashtag pills.
**New concepts:**
- `enctype="multipart/form-data"` — Form encoding required to package and transmit binary files (images) to the backend.
- Static Files vs. Media Files — Static files (CSS/JS) are authored by developers; Media files are uploaded by users at runtime.
- Ephemeral Disks & S3 — EC2 local storage is temporary and lost upon instance recreation; media files must live in centralized, durable object storage like Amazon S3 in production.
- Database Race Condition Protection — Enforcing single-user single-like integrity using a `UniqueConstraint` on the database level rather than just checking application memory.
- Many-to-Many Filtering — Querying reverse relationships (`Post.objects.filter(tags__name=tag_name)`) across join tables.
**Problems faced and fixes:**
- Image uploads were initially ignored by standard form submissions: added `enctype="multipart/form-data"` to the `<form>` element in `post_form.html`.
- Uploaded images failed to render in the browser during development: hooked `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` into `config/urls.py` when `DEBUG=True`.
**Likely questions and my answers:**
1. Q: Why should uploaded user media NOT be stored on the local EC2 server disk in production?
   A: In a production AWS architecture with an Auto Scaling Group behind an Application Load Balancer, EC2 instances are ephemeral (stateless and disposable). When instances scale down or get replaced during deployment, local disk data is permanently lost. Furthermore, an image saved to Instance A would not exist on Instance B, causing 404 errors for visitors routed to Instance B. Uploads must be stored centrally in Amazon S3.
2. Q: What is the purpose of `enctype="multipart/form-data"` in an HTML form?
   A: Default HTML forms use `application/x-www-form-urlencoded`, which encodes data as key-value text pairs unsuitable for binary content. `multipart/form-data` splits the request into separate MIME parts, allowing binary image streams from `<input type="file">` to be sent alongside standard text inputs.
3. Q: How does our database prevent duplicate likes from the same user on the same post?
   A: Through a `UniqueConstraint(fields=['post', 'user'], name='unique_post_user_like')` defined in the `Like` model's `Meta` class. Even under simultaneous concurrent requests, the relational database engine enforces uniqueness and prevents duplicate records.
**Can I honestly put this on my resume?** Yes — Built user interaction systems (comments, likes) with database constraint safeguards, image upload pipelines with media storage routing, and Many-to-Many tag filtering.


---

## Phase 4 — Trending analytics (stage 1, local) (November 12, 2026)
**What I built:** Dedicated `analytics` app with `PostView` and `PostStats` models, anonymous visitor tracking using SHA-256 IP/User-Agent hashing with a 30-minute de-duplication window, time-decay scoring engine, custom Django management command `python manage.py compute_trending`, a 2-column homepage with live trending leaderboard and badges, and a 19-test automated test suite.
**New concepts:**
- Trending Scoring & Time Decay — Using a mathematical gravity function ($(\text{age} + 2)^{1.5}$) in the denominator to balance high raw activity against freshness so old posts don't hold the top spot indefinitely.
- Privacy-Safe Hashing (SHA-256) — Creating anonymous fingerprints of visitors without storing raw IP addresses (PII) to comply with privacy standards (GDPR).
- View De-duplication Window — Enforcing a 30-minute threshold to prevent repeated page reloads from inflating view counts.
- `OneToOneField` — Establishing an isolated 1:1 relationship between `Post` and `PostStats`, keeping high-churn analytics data separate from core blog post attributes.
- Custom Django Management Commands — Decoupling intensive mathematical calculations from HTTP request/response lifecycles, enabling scheduled batch executions.
**Problems faced and fixes:**
- View count rendering race condition: `super().get()` was executed before `record_post_view()`, causing the view count on the initial page load to render as 0 before the database record was committed. Resolved by getting the object and recording the view *prior* to generating the template context.
**Likely questions and my answers:**
1. Q: Why do we include a time-decay factor in the trending score formula rather than simply sorting by total views or likes?
   A: Without time decay in the denominator, older posts that have accumulated views and likes over months would remain permanently at the top of the leaderboard. Time decay applies mathematical decay to post age, ensuring the trending section dynamically highlights articles that are capturing current engagement and momentum.
2. Q: Why do we hash the visitor's IP address instead of storing it directly in the database?
   A: IP addresses are considered Personally Identifiable Information (PII) under privacy regulations like GDPR. Storing raw IPs creates legal liability and data privacy risks. By hashing the IP alongside the browser's User-Agent using SHA-256, we generate a one-way anonymous fingerprint that allows us to de-duplicate visits within a 30-minute window without ever saving sensitive user data.
3. Q: Why did you create a Django management command to compute trending scores instead of calculating them on every page load?
   A: Recalculating scores requires aggregating views, comments, likes, and dates across all published posts in the database. Running these heavy queries on every single HTTP GET request would degrade server response times and fail to scale under high traffic. Moving this computation to a management command allows it to run asynchronously on a schedule (e.g. hourly via cron or AWS EventBridge/Lambda) without impacting web performance.
**Can I honestly put this on my resume?** Yes — Designed an analytics and trending algorithm with time-decay ranking, privacy-compliant view de-duplication, and asynchronous Django management batch commands.


---

## Phase 5 — AI suggestions (Bedrock) (November 12, 2026)
**What I built:** Integrated AI writing assistant with an asynchronous UI in the post editor. Features a dual-engine architecture: an offline content-aware mock generator (`AI_MOCK_MODE=True`) and the modern Amazon Bedrock Converse API (`boto3`) with model ID configured via environment variables. Includes a dynamic hashtag creation endpoint (`/ai/tag/ensure/`), input length boundaries, per-user rate limiting (5 req/min), and an expanded 26-test suite using `unittest.mock`.
**New concepts:**
- Amazon Bedrock & Bedrock Runtime — Managed, serverless AWS service providing API access to foundation models like Amazon Nova Lite (`amazon.nova-lite-v1:0`) and Titan governed by IAM policies without provisioning GPU infrastructure.
- Bedrock Converse API — The unified, model-agnostic AWS SDK interface for conversational and instruction-based model invocations.
- Prompt Engineering & Structured JSON Output — Constraining LLM generation to return strict, machine-readable JSON payloads (`titles`, `hashtags`, `summary`) matching web form schemas.
- Graceful Degradation — Building resilient systems that remain operational when third-party or cloud dependencies fail or throttle, ensuring users can continue writing manually.
- Asynchronous Tag Creation & Selection — Dynamically generating missing Many-to-Many relational rows via background `fetch()` calls to keep client-side selections synchronized with database state.
- API Rate Limiting — Protecting backend endpoints and cloud API quotas from abuse using cached request timestamps.
**Problems faced and fixes:**
- Clicking AI-suggested hashtags didn't select them in the form because new tags did not yet exist in the relational `Tag` table: created an `/ai/tag/ensure/` endpoint to validate, clean, and create tags on demand, immediately adding `<option>` elements to the DOM.
**Likely questions and my answers:**
1. Q: Why use Amazon Bedrock instead of calling a third-party API like OpenAI directly?
   A: Amazon Bedrock runs entirely within the AWS cloud boundary. It can be secured with AWS IAM roles, VPC private endpoints (no data leaves the internal network), and CloudWatch/CloudTrail audit logging. For enterprise applications, Bedrock provides strict data privacy (user prompts are never used to train base models) and eliminates cross-cloud data egress fees when communicating with EC2 or Lambda.
2. Q: What is graceful degradation, and how is it implemented in this AI assistant?
   A: Graceful degradation ensures that if an external component or network call fails, the core user experience continues without crashing. If Bedrock is unreachable or throttled, our API catches the exception and returns a friendly error message to the editor UI. The author is informed without losing any draft content and can proceed to write and publish their post manually.
3. Q: Why does the system use the Bedrock Converse API rather than model-specific invoke commands?
   A: Older Bedrock integrations required model-specific request and response JSON payloads (e.g. Anthropic Claude required different parameters than Amazon Titan or Meta Llama). The modern Converse API provides a unified, cross-model standard, allowing the application to switch underlying foundation models (such as Amazon Nova Lite) via the `BEDROCK_MODEL_ID` environment variable without altering application code.
**Can I honestly put this on my resume?** Yes — Built an AI editorial assistant integrating Amazon Bedrock Runtime (Converse API) with fallback mock engines, structured JSON prompt engineering, and resilient client-side error handling.


---

## Phase 6 — Production readiness (November 12, 2026)
**What I built:** Fully decoupled production-grade configuration using `.env` and `python-dotenv` with a safe, committed `.env.example` template. Generated a fresh cryptographically secure `SECRET_KEY`, enforced `DEBUG=False` as secure-by-default, enabled dynamic database routing (SQLite locally, RDS on AWS), integrated WhiteNoise with content-hashed manifest compression (`collectstatic` bundled 127 assets), added an ALB `/health/` endpoint, and tested local production serving via Waitress WSGI.
**New concepts:**
- 12-Factor App Configuration — Storing credentials, secrets, and environment flags in environment variables so the same codebase runs unmodified across dev, test, and production.
- Security Impact of `DEBUG=True` — Preventing stack trace disclosures that leak passwords, file paths, and secret keys to external visitors.
- WhiteNoise — A WSGI middleware that serves static files directly from Python with gzip/brotli compression and cache-busting manifest hashes without requiring a separate web server.
- WSGI Servers (Gunicorn vs. Waitress vs. `runserver`) — Understanding multi-process POSIX architectures (`gunicorn`) for Linux/EC2 vs. multi-threaded cross-platform servers (`waitress`) for Windows vs. unoptimized development servers (`runserver`).
- Load Balancer Health Checks — The mechanism used by an Application Load Balancer to continuously monitor server health and reroute traffic away from crashed instances.
**Problems faced and fixes:**
- Uploaded media images returned 404 when `DEBUG=False`: WhiteNoise only serves static files (`/static/`), not user uploads (`/media/`), and Django's `static()` helper disables itself when `DEBUG=False`. Fixed by routing `re_path(r'^media/(?P<path>.*)$', serve, ...)` to ensure local media displays during local production testing until Amazon S3 is connected in Phase 8.
**Likely questions and my answers:**
1. Q: Why shouldn't you run `python manage.py runserver` in production, and why can't Gunicorn run natively on Windows?
   A: `runserver` is a single-threaded server intended solely for local development; it is unhardened against denial-of-service attacks and cannot handle concurrent connections. In production, we run a WSGI server like Gunicorn on Linux. Gunicorn relies on POSIX system calls (`fork()` and `fcntl()`) to manage worker processes, which do not exist on Windows. On Windows development environments, we test with Waitress (a multi-threaded production WSGI server) and specify `gunicorn; sys_platform != "win32"` in `requirements.txt` for our target AWS EC2 Linux servers.
2. Q: Why is `DEBUG = True` dangerous in production?
   A: When an unhandled error occurs with `DEBUG = True`, Django presents a diagnostic screen revealing the entire request environment: secret keys, database credentials, server paths, and code context. Attackers can leverage this information to exploit the system. Setting `DEBUG = False` ensures errors show generic, safe pages while details are sent to internal logs.
3. Q: What is the purpose of the `/health/` endpoint and how does an AWS ALB use it?
   A: The `/health/` endpoint returns HTTP 200 OK to indicate that the application is alive and ready to process traffic. The AWS Application Load Balancer (ALB) pings this URL periodically (e.g. every 15–30 seconds). If an EC2 instance becomes unresponsive or returns error codes, the ALB stops sending web requests to that instance and signals the Auto Scaling Group to replace it with a healthy instance.
**Can I honestly put this on my resume?** Yes — Prepared a Django application for cloud deployment following 12-factor principles, configured WhiteNoise static file compression, implemented ALB health-check endpoints, and decoupled environment configurations for AWS RDS and Bedrock.

---

## Phase 8 — S3 media storage (November 19, 2026)
**What I built:** Configured Django 5.2's modern `STORAGES` dictionary with `django-storages` and `boto3` to offload user-uploaded media files to Amazon S3. Configured secure SigV4 query authentication (`AWS_QUERYSTRING_AUTH = True`) and disabled file overwriting (`AWS_S3_FILE_OVERWRITE = False`). Implemented a zero-credential IAM-role-ready architecture that falls back cleanly to local disk storage (`FileSystemStorage`) when `AWS_STORAGE_BUCKET_NAME` is unset. Added isolated unit tests mocking S3 client and connection properties to guarantee zero live AWS network dependencies.
**New concepts:**
- Decoupled Media vs. Static Assets — Static files (CSS/JS) live with application code and are served via WhiteNoise; dynamic media files (user uploads) live in a centralized, durable object store (Amazon S3) independent of EC2 instance lifecycles.
- Django 5.2 `STORAGES` Setting — The unified configuration dictionary introduced in modern Django that replaces deprecated `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE`.
- IAM Role Instance Profiles vs. Static Access Keys — AWS EC2 instances assume IAM Roles via the Instance Metadata Service (IMDS). `boto3` and `django-storages` retrieve temporary credentials automatically, eliminating hard-coded secrets or `.env` credentials in production.
- S3 Presigned URLs (`AWS_QUERYSTRING_AUTH = True`) & SigV4 — Keeping the S3 bucket private with Block Public Access ON while generating cryptographically signed, expiring URLs (`s3v4`) so authorized readers can view uploaded photos securely.
**Problems faced and fixes:**
- Ensuring local development and unit tests continue without an AWS account: wrapped `STORAGES["default"]` configuration in an `if AWS_STORAGE_BUCKET_NAME:` check so the application defaults to local `FileSystemStorage` on developer workstations and switches to S3 automatically when deployed to AWS.
- Presigned S3 image URLs returned HTTP 400 Bad Request in `ap-southeast-2` because `django-storages` generated the global endpoint hostname (`<bucket>.s3.amazonaws.com`): AWS SigV4 requires the host header to match the signing region. Fixed by explicitly configuring `endpoint_url=f"https://s3.{AWS_S3_REGION_NAME}.amazonaws.com"` and `addressing_style="virtual"` inside `STORAGES["default"]["OPTIONS"]`.
**Likely questions and my answers:**
1. Q: Why can't we store user-uploaded images on the EC2 instance's local filesystem in production?
   A: In an Auto Scaling architecture with multiple EC2 instances behind an Application Load Balancer, an image uploaded to one instance would not exist on other instances. Furthermore, EC2 instances are ephemeral: when traffic drops or an instance fails health checks, Auto Scaling terminates it, destroying any local files. Amazon S3 provides centralized, 99.999999999% (11 9s) durable object storage accessible by all instances.
2. Q: Why use IAM Roles instead of storing AWS access keys in environment variables on EC2?
   A: Hardcoded access keys or environment variables can be accidentally leaked, committed to Git, or left on disk. IAM Roles use the EC2 Instance Metadata Service to issue short-lived, automatically rotated temporary credentials. No permanent AWS credentials ever exist on the virtual machine.
3. Q: How does the app display images if the S3 bucket blocks all public access?
   A: With `AWS_QUERYSTRING_AUTH = True`, Django and boto3 sign each media URL using the AWS Signature Version 4 algorithm (`s3v4`), adding an expiration timestamp and cryptographic signature to the query string. The browser fetches the image directly from S3 using the temporary signature, keeping the bucket entirely closed to public anonymous reads.
**Can I honestly put this on my resume?** Yes — Implemented cloud-native media storage in Django 5.2 using `django-storages` and Amazon S3 with IAM instance profile authentication, SigV4 signed URLs, and local filesystem fallback.

---

## Phase 8.1 — Cloud Activity Telemetry & Performance Optimization (November 21, 2026)
**What I built:** Created the `cloudlog` telemetry app to truthfully track and display what cloud services execute behind every action. Implemented `CloudTracker` context manager measuring real operational latencies with `time.perf_counter()`. Instrumented post CRUD, S3 upload sizes, comments, likes, deduplicated views, and AI assist invocations. Added real-time single-post trending recalculation with a 30-second invalidating cache. Created 4 public JSON API endpoints (`/api/cloud-activity/`, `/api/trending/`, `/api/cloud-status/` with IMDSv2 local fallback, and `/api/ai-insights/`). Optimized post list views with `select_related`, `prefetch_related`, and aggregation annotations, bringing N+1 queries down to 5 constant queries.
**New concepts:**
- Cloud Observability & Telemetry — Instrumenting application code to capture granular sub-operation execution times (Django/Gunicorn, RDS/SQLite, S3, Bedrock/Mock AI) without adding external monitoring overhead.
- EC2 Instance Metadata Service (IMDSv2) — A link-local HTTP service (`http://169.254.169.254/latest/api/token`) used by software on EC2 to securely inspect its Availability Zone, Region, and Instance ID using session-oriented token requests to protect against SSRF vulnerabilities.
- N+1 Query Problem & Solutions — Recognizing that looping over models to access foreign keys or related counts triggers individual database queries (N queries for N items). Resolved using SQL `JOIN`s via `select_related()`, multi-table prefetching via `prefetch_related()`, and SQL aggregation `Count()` annotations.
- Cache Invalidation Strategies — Storing frequently computed leaderboard aggregations (e.g. top 10 trending) in a short-lived cache (30s TTL) while actively purging it (`cache.delete()`) whenever an underlying score event occurs (new view, comment, or like).
**Problems faced and fixes:**
- `PostListView` executed 15 queries on a 5-post page because the template called `post.likes.count` and `post.comments.count` for every post: updated `PostListView.get_queryset()` to annotate `likes_count` and `comments_count` directly in SQL and updated templates to reference the annotated values, achieving 5 constant queries.
**Likely questions and my answers:**
1. Q: What is the N+1 query problem, and how did you diagnose and eliminate it?
   A: The N+1 query problem occurs when fetching a list of items requires 1 query for the parent records and N additional queries for each record's related data (e.g. author, tags, comment counts). We diagnosed it using `assertNumQueries()`, which captured 15 queries for 5 posts. We eliminated it by using `select_related('author')` for a single SQL JOIN, `prefetch_related('tags')` to load all tags in 1 query, and `annotate(likes_count=Count(...))` to compute totals in the initial SELECT statement, reducing it to constant queries.
2. Q: What is IMDSv2 and why is it preferred over IMDSv1?
   A: AWS Instance Metadata Service Version 2 (IMDSv2) uses session-oriented requests requiring a `PUT` request with a token header (`X-aws-ec2-metadata-token`) before retrieving metadata. This mitigates Server-Side Request Forgery (SSRF) and open reverse proxy vulnerabilities that previously allowed attackers to exploit simple `GET` requests in IMDSv1.
3. Q: How does the application ensure telemetry tracking never degrades reliability?
   A: Telemetry measurements use Python's built-in `time.perf_counter()` which adds microsecond overhead. Committing `ActivityEvent` models is wrapped in exception handlers so that any logging or telemetry failure is silently handled, guaranteeing that primary user workflows (creating posts, comments, likes) never fail due to monitoring errors.
**Can I honestly put this on my resume?** Yes — Built an in-app cloud telemetry engine tracking granular sub-service latencies (EC2, S3, RDS, Bedrock), optimized Django ORM queries eliminating N+1 bottlenecks, and integrated IMDSv2 infrastructure discovery endpoints.

---

## Phase 8.2 — Frontend Modernization, Masonry Feed, & AI Generation Refinement (November 21, 2026)
**What I built:** Executed a full UI/UX overhaul across the application. Replaced the top navbar with a collapsible left sidebar icon rail (~72px expanding to 230px on hover/toggle, converting to bottom navigation on mobile). Added a top search bar and global status strip displaying "Health: 200 OK", region, DB engine, storage type, and AI mode. Rebuilt the home feed into a pure Masonry card stream using 3 responsive column containers that append incoming cards to the shortest column without reflow jumping. Added infinite scroll using modern `IntersectionObserver` fetching 12-item JSON batches with duplicate rejection, skeleton loading, and noscript fallback. Prevented cumulative layout shift (CLS) by storing `image_width` and `image_height` via Pillow and setting explicit CSS `aspect-ratio` on all images. Built full dedicated pages for Trending Analytics (hero top 3 with score breakdown bars, rank changes, formula banner, and 15s auto-refresh), Cloud Activity (interactive pipeline latency viewer), AWS Cloud Architecture, and AI Insights. Refined the AI suggestion generator with stop-word filtering and 4 distinct title styles (statement, question, short headline, story).
**New concepts:**
- Cumulative Layout Shift (CLS) & Aspect-Ratio — When images load without explicit dimensions, content jumps as image bytes arrive, causing poor UX. By storing image dimensions in the database on upload and rendering `aspect-ratio: width / height`, browsers reserve exact vertical space prior to network completion.
- Column-Container Masonry vs. CSS Multi-Column — CSS `column-count` automatically reflows all items across columns whenever new items are appended via infinite scroll, causing visual flickering. Using 3 separate container columns and appending new elements to the currently shortest column maintains stable vertical layout while preserving responsive breakpoints.
- IntersectionObserver API — A high-performance browser API that asynchronously observes when a target element (sentinel) enters the viewport, replacing expensive scroll event listeners for infinite scrolling.
- De-Duplication Sets in Dynamic Feeds — Managing a JavaScript `Set` of post IDs already present in the DOM prevents duplicated items if new records are published while a user is actively scrolling.
**Problems faced and fixes:**
- Infinite scroll cards reflowed and rearranged jarringly when using CSS multi-columns: implemented 3 separate column containers (`#col-0`, `#col-1`, `#col-2`) with JavaScript `appendCardToShortest()` measuring container heights and appending to the shortest column, delivering smooth infinite scrolling.
- `assertNumQueries` test failed after removing sidebar widgets: the test previously expected 5 queries because the sidebar rendered trending post tags. With widgets moved to dedicated pages, `PostListView` required only 4 queries; updated test assertions to accurately reflect the 4 constant queries.
**Likely questions and my answers:**
1. Q: How does the application prevent layout jumps (CLS) when loading user images in the masonry feed?
   A: On model save, Pillow inspects the uploaded image binary to record `image_width` and `image_height` in nullable database columns. In the HTML template, `<img>` tags declare `aspect-ratio: width / height`, `loading="lazy"`, and `decoding="async"`. The browser calculates and reserves the exact height before the image file is downloaded over the network, completely eliminating layout shifting.
2. Q: Why did you use IntersectionObserver instead of a scroll event listener for endless vertical scroll?
   A: A traditional `window.addEventListener('scroll')` runs on every single pixel scrolled, which requires throttling/debouncing and can cause main-thread jank. The modern `IntersectionObserver` API runs off the main thread and notifies the application only when a target sentinel element crosses a specified viewport threshold (e.g. 400px before reaching the bottom).
3. Q: How does the Mock AI engine generate realistic suggestions without calling Bedrock?
   A: The mock service strips English stop words (prepositions, articles, fillers) to extract high-intent keywords for hashtags. It parses the author's primary sentence and generates 4 distinct title styles (declarative statement, curiosity question, punchy headline, and story-style framing) without using generic buzzwords unless the post explicitly discusses technology.
**Can I honestly put this on my resume?** Yes — Built a responsive Masonry web feed with endless vertical scrolling using IntersectionObserver, eliminated Cumulative Layout Shift via Pillow-calculated aspect ratios, and developed real-time cloud telemetry and analytics dashboards.

---

## Phase 8.3 — Frontend Polish & Post Detail Experience (November 21, 2026)
**What I built:** Polished the application navigation and post interaction experience. Centered the `+` icon in the collapsed sidebar button and removed duplicate plus text. Configured the expanded sidebar to overlay content with high z-index and drop-shadow without shifting page content. Pinned "Settings" and CSRF-protected "Logout" to the sidebar bottom. Created a dedicated Settings page (`/settings/`) supporting profile inspection, password change via Django's `PasswordChangeView`, theme switching (light/dark), and status strip visibility toggling persisted in `localStorage`. Overhauled the Post Detail view into an asymmetric 55% / 45% sticky two-column layout on desktop: the left side anchors media with `object-fit: contain` and fullscreen lightbox modal support, while the right side organizes post details in strict hierarchy (title, author/date, basic metrics, hashtag chips, body, like/action buttons, newest comments first, and comment form). Added browser-history-aware back navigation and real-time cloud timing toasts.
**New concepts:**
- Sticky Two-Column Reading Layouts — Positioning media containers with `position: sticky; top: 75px; align-self: flex-start;` keeps visual context anchored on screen during prolonged scrolling through detailed technical discussion.
- Zero-Library Lightbox Modals — Leveraging Bootstrap 5's native modal system (`data-bs-toggle="modal"`) to display high-resolution imagery without importing heavy external viewer dependencies.
- Head Theme Preload Execution — Executing a tiny blocking script in `<head>` to read `localStorage` and set `data-bs-theme` before CSS parsing begins, preventing white screen flashes when dark mode is enabled.
- Browser History Referrer Checks — Checking `document.referrer` against `window.location.host` enables intelligent `history.back()` navigation that preserves search filters and infinite scroll position when returning from post details.
**Problems faced and fixes:**
- Expanding sidebar shifted page layout horizontally: anchored `.app-wrapper` at a constant `margin-left: 72px` and set `.sidebar-rail` to `z-index: 1050`, allowing the rail to smoothly overlay the page without moving the top search bar or status strip.
**Likely questions and my answers:**
1. Q: How does the theme toggle prevent a flash of light mode when a user reloads the page with dark mode enabled?
   A: Browsers parse and execute synchronous scripts in `<head>` before rendering DOM elements. By placing an IIFE in the `<head>` that reads `localStorage.getItem('appTheme')` and immediately sets `data-bs-theme` on `document.documentElement`, the initial paint renders in the user's preferred theme without any visual flashing.
2. Q: Why use Django's built-in `PasswordChangeView` instead of writing custom password-handling views?
   A: Django's `PasswordChangeView` utilizes `PasswordChangeForm`, which automatically validates old passwords, applies all configured password validators (length, common passwords, numeric, similarity), securely hashes new credentials via PBKDF2/SHA256, and calls `update_session_auth_hash()` to maintain the user's active session without logging them out.
**Can I honestly put this on my resume?** Yes — Implemented a modern sticky multi-column post viewer with zero-dependency lightbox modal, history-aware navigation, user settings with password rotation, and client-side theme persistence.

---

## Phase 8.4 — Feed Restoration, Toast Consolidation & Mobile Navigation Polish (November 23, 2026)
**What I built:** Fixed feed state loss upon navigating back from post details by establishing a resilient hybrid rendering model: the initial 12-item batch is always rendered directly on the server in HTML, while client-side script handles subsequent batches, bfcache (`pageshow`) reconnection, and sequential batch restoration from `sessionStorage`. Converted "Back to all posts" into a standard relative `{% url 'post_list' %}` URL to work reliably behind Nginx reverse proxies. Consolidated flash notifications into a single bottom-right toast container that auto-dismisses after 4 seconds and de-duplicates via `sessionStorage` (preventing alert banner duplication or repeating animations). Added a mobile "More" offcanvas bottom sheet housing Architecture and AI Insights pages, and served an inline cloud SVG favicon preventing console 404 errors. Added 4 unit tests covering server-side card rendering, feed cache-control headers, single consolidated toasts, and favicon routing.
**New concepts:**
- Back-Forward Cache (bfcache) Lifecycle — Modern browsers preserve the entire in-memory state of visited pages for instant back/forward navigation. When restoring from bfcache, `DOMContentLoaded` is bypassed and `pageshow` fires with `event.persisted = true`. Event listeners and observers (such as `IntersectionObserver`) must explicitly listen to `pageshow` to re-synchronize state.
- Server-First Progressive Enhancement — Ensuring the server generates complete DOM markup for the initial data batch means the page is instantly readable and usable even if client JavaScript fails, network drops, or browser extensions interfere.
- Notification De-Duplication & Single Toast Container — Instead of scattering flash banners across the top of the viewport and rendering duplicate toasts in the corner, routing all application events through a single toast container with client-side event tracking guarantees clean, non-intrusive notifications.
- HTTP Cache-Control on Dynamic Feed Endpoints — Using `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` ensures browsers and proxies never store or serve stale, empty, or cached pagination fragments during dynamic feed scrolling.
**Problems faced and fixes:**
- Clicking "Back to all posts" restored a blank feed because `post_detail.html` executed `history.back()`, which did not re-run `DOMContentLoaded` in `post_list.html`: removed `history.back()` interception in favor of a standard relative link, and re-initialized the feed and re-attached the `IntersectionObserver` on both `DOMContentLoaded` and `pageshow`.
- Toasts looped and bounced because `SuccessMessageMixin` added a message while `form_valid()` added a second, and the HTML hard-coded `.show` while JS called `.show()`: removed `SuccessMessageMixin`, unified messages into one cloud-latency string in `form_valid()`, and removed static `.show` classes from HTML.
**Likely questions and my answers:**
1. Q: Why did the infinite scroll feed break when returning from a post detail page, and how did you resolve it?
   A: Modern browsers restore previous pages from the Back-Forward Cache (bfcache) rather than reloading them, which fires the `pageshow` event instead of `DOMContentLoaded`. Because our observer was set up only in `DOMContentLoaded`, the observer remained detached upon returning. We resolved it by converting the Back button into a standard relative URL (`{% url 'post_list' %}`), listening to both `DOMContentLoaded` and `pageshow` (`event.persisted`), ensuring the first batch of 12 posts is always rendered into the HTML by Django on the server, and sequentially restoring any extra loaded batches from `sessionStorage`.
2. Q: What is `Cache-Control: no-store` and why is it essential for API feed endpoints?
   A: `Cache-Control: no-store` instructs both the browser and intermediary HTTP proxies (such as CloudFront or Nginx) to never store any version of the response in cache. For infinite-scroll JSON endpoints like `/posts/feed/?page=2`, this prevents the browser from serving an empty or stale cached batch when users navigate back and forth or new posts are published.
**Can I honestly put this on my resume?** Yes — Engineered a bfcache-resilient infinite scroll feed with server-rendered fallback and scroll position restoration, consolidated cloud telemetry toasts, and built mobile offcanvas navigation.

---

## Phase 8.5 — 4-Column Desktop Masonry Layout & 16-Post Batching (November 23, 2026)
**What I built:** Expanded the desktop feed from 3 to 4 columns on screens $\ge 1200\text{px}$ (3 columns from $900\text{px}$, 2 from $576\text{px}$, 1 below that). Sourced the responsive column counts from a single JavaScript configuration array (`COLUMN_BREAKPOINTS`). Implemented dynamic card rebalancing upon window resize across breakpoints, redistributing cards across active columns in stable DOM order without reloading. Increased batch size from 12 to 16 posts across both server rendering and the JSON feed API (`post_feed_api`), matching 4-column symmetry ($16 \div 4 = 4$). Compacted the post cards for narrower column widths: title clamped to 2 lines with ellipsis, hashtags limited to 2 chips on a single nowrap line, padding reduced to `0.75rem`, and author metadata and like/comment counts aligned on a single line. Updated unit tests to expect 16-item initial renders and 16-item pagination batches.
**New concepts:**
- Single Source of Truth for Layout Breakpoints — Defining breakpoint thresholds and column counts in a single centralized config array avoids dispersed magic numbers across media queries and resize listeners.
- Dynamic Masonry Rebalancing — When screen size crosses a responsive threshold, wiping column contents and re-appending elements in original DOM order using `appendCardToShortest()` keeps heights balanced and card order stable without reloading or refetching.
**Problems faced and fixes:**
- Cards in 4 columns felt visually cramped with multi-line tags and 3-line titles: clamped titles to 2 lines with CSS `-webkit-line-clamp: 2`, sliced hashtags to a maximum of 2 chips on one line, and aligned author and metrics on a single row.
**Likely questions and my answers:**
1. Q: How does the 4-column masonry layout handle browser resizing without flickering or losing user scroll?
   A: The layout defines a single JavaScript breakpoint structure `COLUMN_BREAKPOINTS`. A debounced resize event listener checks if the active column count changed. If so, it preserves the DOM array of `.post-feed-card` elements, clears the column containers, and sequentially appends each card to the currently shortest active column. Cards stay in chronological order and heights remain balanced without any network requests.
**Can I honestly put this on my resume?** Yes — Built a responsive 4-column Masonry feed with dynamic runtime rebalancing and optimized compact card typography.






