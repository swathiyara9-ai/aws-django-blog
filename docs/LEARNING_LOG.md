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
- Amazon Bedrock & Bedrock Runtime — Managed, serverless AWS service providing API access to foundation models (Claude, Titan) governed by IAM policies without provisioning GPU infrastructure.
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
   A: Older Bedrock integrations required model-specific request and response JSON payloads (e.g. Anthropic Claude required different parameters than Amazon Titan or Meta Llama). The modern Converse API provides a unified, cross-model standard, allowing the application to switch underlying foundation models via the `BEDROCK_MODEL_ID` environment variable without altering application code.
**Can I honestly put this on my resume?** Yes — Built an AI editorial assistant integrating Amazon Bedrock Runtime (Converse API) with fallback mock engines, structured JSON prompt engineering, and resilient client-side error handling.
