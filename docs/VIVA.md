# Viva & Technical Interview Preparation Guide

This guide contains 15 likely viva and interview questions about the AWS Django Blog platform, with short, simple, and technically precise answers tailored for an undergraduate B.Tech IT engineering review.

---

### Q1. Why did you use Amazon VPC and Security Groups? How do Security Groups differ from Network ACLs?
**Answer:**
A **Virtual Private Cloud (VPC)** provides an isolated virtual network inside AWS where our servers and databases run securely away from the public internet.
- **Security Groups** act as virtual firewalls at the *instance level*. They are **stateful** (if inbound traffic is allowed, outbound return traffic is automatically allowed) and evaluate all rules before deciding to allow traffic.
- **Network ACLs (NACLs)** act as subnet-level firewalls. They are **stateless** (return traffic must be explicitly allowed) and process rules in strict numerical order.
In our project, the EC2 instance accepts HTTP on port 80/443, while the RDS PostgreSQL database accepts connections on port 5432 *strictly* from the EC2 security group, blocking direct internet access to the database.

---

### Q2. What is the difference between SQLite and Amazon RDS in this project?
**Answer:**
- **SQLite** is a serverless, file-based database. It writes directly to a single disk file (`db.sqlite3`). It is fast and zero-configuration for local development and unit tests, but it locks the whole database file during writes, making it unsuitable for multi-user production concurrency.
- **Amazon RDS (PostgreSQL)** is a fully managed client-server database. It handles concurrent connections, transactions, automated daily backups, point-in-time recovery, and OS security patching.
Our `config/settings.py` automatically switches between SQLite locally and RDS in production based on whether `DB_ENGINE` is set in `.env`.

---

### Q3. How does Amazon S3 handle post images, and why is an EC2 IAM Role safer than hardcoding AWS Access Keys?
**Answer:**
User-uploaded post hero images are stored in an Amazon S3 bucket (`aws-django-blog-media-20261119`) using `django-storages` and `boto3`.
- **Hardcoding keys** (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) in `.env` or code is dangerous because keys can be accidentally committed to GitHub or exposed if the server is compromised.
- An **IAM Role** attached to the EC2 instance profile uses AWS Security Token Service (STS) to deliver temporary, automatically rotated credentials via the Instance Metadata Service (IMDSv2). No permanent secret keys ever exist on the server filesystem.

---

### Q4. What is the trending score algorithm formula, and how does time decay prevent older viral posts from dominating forever?
**Answer:**
We use a Hacker News-inspired gravity formula:

$$\text{Score} = \frac{\text{views} + (3 \times \text{likes}) + (5 \times \text{comments})}{(\text{age\_hours} + 2)^{1.5}}$$

- **Weighted Engagement**: Comments ($5\times$) reflect deeper discussion than likes ($3\times$) or passive views ($1\times$).
- **Time Decay**: The denominator $(\text{age\_hours} + 2)^{1.5}$ grows super-linearly over time. Even if an older post accumulated hundreds of views, its denominator grows so large that fresh, active posts quickly overtake it. The `+2` prevents division by zero for newly published posts.

---

### Q5. How does view de-duplication work, and why do you hash visitor IP and User-Agent instead of storing raw IP addresses?
**Answer:**
When a user visits `/post/<slug>/`, `analytics/services.py` calculates a SHA-256 hash of `visitor_ip + user_agent + SECRET_KEY_salt`. If a view record with that hash exists for the same post within the last **30 minutes**, the view is ignored.
- **Privacy & GDPR/DPDP Compliance**: Raw IP addresses are personally identifiable information (PII). Storing SHA-256 hashes ensures we can de-duplicate repeated visits without retaining sensitive user IP addresses in our database.

---

### Q6. How are Amazon Bedrock AI suggestions generated and validated before displaying them to authors?
**Answer:**
When an author clicks "Suggest with AI":
1. The post draft text is sent to `/api/ai-suggestions/`.
2. `ai_assist/services.py` sends a structured prompt to Amazon Bedrock invoking **Amazon Nova Lite** (`amazon.nova-lite-v1:0` in `ap-southeast-2`).
3. The prompt instructs the model to return valid JSON with:
   - 4 distinct title styles (*Statement*, *Question*, *Headline*, *Story*)
   - Relevant hashtags
   - A one-sentence summary
4. The service validates and sanitizes the JSON response: ensures all required keys exist, strips markdown code blocks, normalizes hashtags, and truncates text to field limits before returning to the browser.
5. If Bedrock is unreachable or in mock mode, a built-in mock AI engine generates intelligent context-aware suggestions without failing.

---

### Q7. Why do we run Gunicorn behind Nginx instead of exposing Django or Gunicorn directly to the internet?
**Answer:**
- **Nginx** is an asynchronous, event-driven web server. It handles slow clients, buffers slow request uploads, terminates SSL/TLS connections, prevents slowloris DDoS attacks, and directly serves cached static assets.
- **Gunicorn** is a synchronous pre-fork WSGI application server designed specifically to run Python code.
If Gunicorn were exposed directly, a slow client on a poor mobile connection would tie up a Python worker for seconds just downloading bytes. Nginx buffers the request completely and hands it to Gunicorn over a lightning-fast local Unix socket, keeping Python workers free for business logic.

---

### Q8. Why are configuration values kept in environment variables instead of hardcoded in `settings.py`?
**Answer:**
This follows the **Twelve-Factor App methodology (Config principle)**:
1. **Security**: Secrets (database passwords, Django `SECRET_KEY`, AWS bucket names) are never committed to version control.
2. **Environment Portability**: The same codebase runs locally on a laptop (SQLite, Mock AI, `DEBUG=True`) and on AWS EC2 (RDS PostgreSQL, Amazon Bedrock, `DEBUG=False`) simply by changing the `.env` file without altering a single line of code.

---

### Q9. What is WhiteNoise, and why do we use WhiteNoise for static files and S3 for media uploads?
**Answer:**
- **Static files** (CSS, JavaScript, SVG logos, Bootstrap) are authored by developers and bundled with the codebase during `collectstatic`. **WhiteNoise** sits directly in Django's WSGI pipeline, compresses static files with gzip/brotli, adds unique content hashes for cache-busting, and serves them with immutable cache headers. This avoids S3 cross-origin (CORS) complexity and costs for static assets.
- **Media files** (post cover images) are dynamic and uploaded by end-users at runtime. Because EC2 instances have ephemeral local storage and may be terminated or scaled out, user uploads must be stored in a centralized, durable object storage service like **Amazon S3**.

---

### Q10. How does the 4-column responsive masonry feed work without layout shifts (CLS)?
**Answer:**
1. **Zero Cumulative Layout Shift (CLS)**: When an author uploads an image, Pillow inspects the image dimensions and saves `image_width` and `image_height` to the database. In templates, `<img>` tags declare `aspect-ratio: width / height`, `loading="lazy"`, and `decoding="async"`. The browser calculates and reserves the exact vertical height before the image file is downloaded.
2. **Masonry Column Balancing**: The page container holds 4 separate column containers. A JavaScript loop evaluates the client height of each column and appends each new card to the **shortest column**.
3. **Resize Rebalancing**: When crossing responsive breakpoints (1200px: 4 cols, 900px: 3 cols, 576px: 2 cols, below: 1 col), existing cards are re-distributed in stable DOM order across the active columns without re-fetching or reloading the page.

---

### Q11. How does the application maintain feed state and scroll position when returning from a post detail page (bfcache)?
**Answer:**
Modern browsers store visited pages in the **Back-Forward Cache (bfcache)**.
- When clicking "Back to all posts", the browser fires the `pageshow` event with `event.persisted = true` rather than reloading `DOMContentLoaded`.
- The feed script listens to both `DOMContentLoaded` and `pageshow`.
- The first 16-post batch is **always rendered directly into the HTML on the server by Django**, ensuring instant visibility even without JS.
- Extra loaded batches and scroll coordinates are stored in `sessionStorage` and restored sequentially on return, re-attaching the `IntersectionObserver` so infinite scrolling resumes seamlessly.

---

### Q12. How does the toast notification system de-duplicate messages and integrate cloud latency timings?
**Answer:**
Previously, Django messages and client-side cloud timing alerts created multiple bouncing banners.
- We consolidated notifications into a **single fixed toast container** in the bottom-right viewport.
- In views (`CreatePostView`, `UpdatePostView`), a timing tracker measures database write time and S3 upload time.
- The view packages these into a unified message (e.g. `Post saved — RDS 14 ms, S3 118 ms`).
- The client-side toast script checks `sessionStorage` with an event hash to guarantee the toast renders exactly once, slides in smoothly, and auto-dismisses after 4 seconds.

---

### Q13. What happens if Amazon Bedrock or the AWS network fails when an author requests AI suggestions?
**Answer:**
The system is built with **graceful degradation (fail-safe)**:
- In `ai_assist/services.py`, all `boto3` calls are wrapped in `ClientError` and timeout exception handlers.
- If Bedrock fails, throttles, or credentials are unavailable, the function catches the exception, logs a warning, and automatically switches to the **Mock AI engine**.
- The mock engine parses the post title and body, removes stop words, generates 4 title variations, extracts hashtags, and returns clean JSON.
- The author never encounters a 500 error or a broken form.

---

### Q14. What are the security settings checked by `python manage.py check --deploy`, and when should HTTPS flags be turned on?
**Answer:**
`check --deploy` inspects production security settings:
- `SECRET_KEY`: Must not be default or easily guessed.
- `DEBUG = False`: Prevents revealing stack traces, database schema, and environment variables on 500 errors.
- `SECURE_BROWSER_XSS_FILTER` & `SECURE_CONTENT_TYPE_NOSNIFF`: Prevents MIME-type sniffing attacks.
- `X_FRAME_OPTIONS = 'DENY'`: Prevents clickjacking in iframes.
- **HTTPS Settings** (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`): These ensure cookies are only transmitted over TLS encryption. In our app, they are controlled via environment variables. On HTTP-only demo deployments, they remain `False` to prevent lockouts, and switch to `True` once a domain and SSL certificate (via CloudFront/ACM) are configured.

---

### Q15. What architectural components are currently built and deployed versus planned for future scalability?
**Answer:**
To remain honest about our project's current deployment:
- **Built & Deployed on AWS**:
  - Single EC2 instance (Amazon Linux 2023) running Nginx reverse proxy, Gunicorn WSGI, and Django 5.2.
  - Amazon RDS PostgreSQL database in a private subnet.
  - Amazon S3 bucket (`aws-django-blog-media-20261119`) with Block Public Access for media files.
  - IAM Instance Profile (`EC2-Django-App-Role`) for credential-free AWS access.
  - Amazon Bedrock Nova Lite integration (tested with offline mock fallback, boto3 code live ready).
- **Planned for Future Scale-Out**:
  - **Application Load Balancer (ALB)** across multiple availability zones.
  - **EC2 Auto Scaling Group (ASG)** to scale instances dynamically based on CPU utilization.
  - **CloudFront CDN + AWS Certificate Manager (ACM)** for global HTTPS edge distribution.
  - **AWS Lambda + DynamoDB** for serverless, high-frequency view count ingest.
