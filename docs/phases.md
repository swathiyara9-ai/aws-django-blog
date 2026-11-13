# Phases — Detailed Build Guide

Companion to `TASKS.md` (checklist). This file explains **what to build, why, how to test it, and what to say in an interview** for each phase.

Rules for every phase:
- Work on one phase at a time. Confirm results before moving on.
- Run the manual tests before ticking the box in `TASKS.md`.
- Add an entry to `LEARNING_LOG.md` when the phase is done.

---

## Part A — Build the app locally (Phases 0–6)

### Phase 0 — Local setup
**Goal:** A blank Django site running on your laptop.
**Why:** Fix Django problems locally before AWS adds new ones.

**Steps**
1. Create the folder and virtual environment.
2. `pip install django`
3. `django-admin startproject config .` then `python manage.py startapp blog`
4. `git init`, add `.gitignore` (venv, `.env`, `db.sqlite3`, `media/`, `__pycache__/`)
5. `pip freeze > requirements.txt`

**Concepts:** virtual environment, project vs app, `manage.py`, `.gitignore`.
**Test:** `python manage.py runserver` shows the welcome page.
**Interview Q:** Why do we use a virtual environment?

---

### Phase 1 — Models and admin
**Goal:** The database structure for the blog, managed through Django admin.
**Why:** Everything else (pages, comments, analytics) stores data in these tables.

**Steps**
1. Add `'blog'` to `INSTALLED_APPS` in `config/settings.py`.
2. Write models in `blog/models.py`: `Tag`, `Post`, `Comment`, `Like` (fields in `DATABASE.md`).
3. `python manage.py makemigrations` then `python manage.py migrate`
4. Register models in `blog/admin.py`.
5. `python manage.py createsuperuser`, open `/admin/`.

**Concepts:** ORM (Python class = table), migration (a versioned change to the database), ForeignKey, ManyToMany, admin site.
**Test:** Create a tag and a post with that tag in admin; the post appears in the list.
**Interview Q:** What is a migration and why not edit the database by hand?

---

### Phase 2 — Authentication and post CRUD
**Goal:** Users can register, log in, and manage their own posts.

**Steps**
1. `templates/base.html` with Bootstrap (CDN) and a navbar.
2. Auth: use Django's built-in `LoginView` / `LogoutView`; write a register view with `UserCreationForm`.
3. Views: `PostListView` (paginate), `PostDetailView`, `PostCreateView`, `PostUpdateView`, `PostDeleteView`.
4. Protect create with `LoginRequiredMixin`; protect edit/delete with `UserPassesTestMixin` (author only).
5. Auto-generate `slug` from the title; make it unique.
6. URLs and templates for each view.

**Concepts:** class-based views, mixins, forms, CSRF token, template inheritance, authentication vs authorization.
**Test:**
- Register, log in, create a post.
- Log in as a second user: you must NOT be able to edit or delete the first user's post (try the URL directly).
- Anonymous visitors can read posts but not create them.
**Interview Q:** Difference between authentication and authorization? How did you enforce "author only"?

---

### Phase 3 — Comments, likes, images, tags
**Goal:** Interaction features around a post.

**Steps**
1. Comment form on the detail page (login required); show comments newest first.
2. Like/unlike toggle (one like per user per post, enforced by the unique constraint).
3. `pip install Pillow`; set `MEDIA_URL` and `MEDIA_ROOT`; serve media in development via `urls.py`.
4. Image upload field on the post form; show it on list and detail pages.
5. Tag pages: `/tag/<name>/` lists posts with that tag.

**Concepts:** file uploads (`enctype="multipart/form-data"`), media vs static files, unique constraints.
**Test:** Upload an image and see it displayed; like twice and the count stays 1; clicking a tag filters posts.
**Interview Q:** Why should uploaded images not live on the EC2 disk in production? (Instances are replaceable under Auto Scaling, so files must live in S3.)

---

### Phase 4 — Trending analytics (stage 1, local)
**Goal:** A Trending section ranked by activity.
**Why this is a "new" feature:** it turns raw activity into a ranking you can explain.

**Steps**
1. Create app: `python manage.py startapp analytics`.
2. Models: `PostView`, `PostStats` (see `DATABASE.md`).
3. In the post detail view, record a view. Store a hash of IP + user-agent, never the raw IP. Ignore repeat views from the same visitor within a time window (for example 30 minutes).
4. `analytics/services.py`: function `compute_scores()` using the formula in `PRD.md`.
5. Management command `python manage.py compute_trending` that updates `PostStats`.
6. Home page shows the top 5 posts by score.

**Concepts:** de-duplication, scoring/ranking, management commands, privacy (hashing).
**Test:** Create three posts, give one many views, comments and likes, run `compute_trending`; the Trending order changes accordingly.
**Interview Q:** Why divide by age? (Without decay, old popular posts would stay on top forever.) Why hash the IP?

---

### Phase 5 — AI suggestions with Amazon Bedrock
**Goal:** A "Suggest" button that proposes titles, hashtags and a summary.

**Steps**
1. `pip install boto3`; run `aws configure` (use an IAM user or profile with minimal Bedrock permission, not your root account).
2. In the AWS console, confirm the chosen Bedrock model (Amazon Nova Lite `amazon.nova-lite-v1:0` in `ap-southeast-2`) is available and enabled in your region.
3. `python manage.py startapp ai_assist`.
4. `ai_assist/services.py`: build a prompt from the post body; call Bedrock Runtime via the Converse API; ask for **JSON only** with keys `titles` (3–5), `hashtags` (5–8), `summary` (one line); parse with `json.JSONDecoder().raw_decode` and validate.
5. Endpoint `POST /ai/suggest/` (login required): check input length, apply a simple per-user rate limit, return JSON.
6. In the editor template, a Suggest button uses `fetch()` (with the CSRF token) and shows clickable suggestions that fill the title, tags and summary fields.
7. Handle failures: timeout, throttling, invalid JSON → friendly message; the editor must still save posts.
8. Put the model id in a setting, `BEDROCK_MODEL_ID` (default `amazon.nova-lite-v1:0`), and region `AWS_REGION` (default `ap-southeast-2`), read from environment variables.

**Concepts:** boto3 client, Converse API, IAM permissions (`bedrock:InvokeModel` scoped strictly to `arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0`), prompt design, structured output, input validation, rate limiting, graceful degradation.
**Test:** Suggestions appear for a long post; a very short post shows a helpful message; with credentials removed the editor still works and shows an error message.
**Interview Q:** How do you handle the AI returning malformed output? How do you control cost?

---

### Phase 6 — Production readiness
**Goal:** The same code runs on a server without changes, only configuration.

**Steps**
1. Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, database settings, bucket name and `BEDROCK_MODEL_ID` to environment variables.
2. Add `gunicorn` and `whitenoise` (for static files); run `python manage.py collectstatic`.
3. Add a `/health/` view that returns HTTP 200 (used later by the ALB).
4. Make the database configurable: SQLite when no DB variables are set, RDS otherwise.
5. Pin all packages in `requirements.txt`.
6. Test with `DEBUG=False` and `gunicorn config.wsgi`.

**Concepts:** twelve-factor configuration, WSGI server vs development server, static file collection.
**Test:** App works with `DEBUG=False`; static files load; `/health/` returns 200.
**Interview Q:** Why not use `runserver` in production?

---

## Part B — Deploy on AWS (Phases 7–10)

> Before Phase 7: create an **AWS Budget alert**, choose the region, and confirm the Bedrock model is available there.

### Phase 7 — Networking and safety
**Goal:** A private network with firewalls set up the right way.

**Steps**
1. Create a VPC (for example `10.0.0.0/16`).
2. Two public subnets and two private subnets across two Availability Zones.
3. Internet Gateway; route table for public subnets to the Internet Gateway.
4. Security groups:
   - `alb-sg`: inbound 80/443 from the internet
   - `app-sg`: inbound app port (e.g. 8000) **from `alb-sg` only**
   - `db-sg`: inbound DB port **from `app-sg` only**
5. S3 Gateway VPC Endpoint (free) attached to the private route tables.
6. Decide on outbound internet for private subnets (NAT Gateway costs money; see `ARCHITECTURE.md` cost notes).

**Concepts:** CIDR, subnets, route tables, internet gateway, NAT, security groups (stateful firewalls), multi-AZ.
**Test:** Diagram your VPC and compare with `ARCHITECTURE.md`; verify each security group's rules.
**Interview Q:** Why are the database and app servers in private subnets? Why a security-group chain instead of IP ranges?

---

### Phase 8 — RDS and S3
**Goal:** Real database and file storage in the cloud.

**Steps**
1. RDS: create a DB subnet group (private subnets), the engine you chose, a small instance class, not publicly accessible, `db-sg` attached.
2. Install the DB driver (`mysqlclient` or `psycopg2-binary`) and set the DB environment variables.
3. S3: create a media bucket with **Block Public Access ON**.
4. `pip install django-storages`; configure the S3 storage backend for media.
5. IAM role (instance profile) for EC2 allowing only: read/write to that bucket and `bedrock:InvokeModel` scoped strictly to `arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0`.
6. Launch one test EC2 instance in a subnet with this role; run migrations against RDS; create a post with an image.

**Concepts:** managed databases, subnet groups, IAM roles vs access keys, least privilege, object storage.
**Test:** Post saved in RDS; image object visible in S3; no access keys exist on the server.
**Interview Q:** Why use an IAM role instead of access keys on the server?

---

### Phase 9 — EC2, ALB and Auto Scaling
**Goal:** A load-balanced app that heals itself and scales.

**Steps**
1. Prepare a **user-data** script: install Python, fetch your code, install requirements, set environment variables, start Gunicorn (as a service).
2. Create a **Launch Template** (AMI, instance type, `app-sg`, IAM instance profile, user data).
3. Target group with health check path `/health/`.
4. Application Load Balancer in public subnets with `alb-sg`; listener 80 forwarding to the target group.
5. Auto Scaling Group across the two private/public subnets: min 2, desired 2, max 3–4; attach to the target group.
6. Scaling policy: target tracking on average CPU (for example 50%).
7. Update `ALLOWED_HOSTS` for the ALB DNS name.

**Concepts:** launch template, user data, target group, health checks, desired/min/max capacity, target tracking scaling.
**Test:**
- Open the ALB DNS name and see the blog.
- Terminate one instance: the site stays up and a new instance appears.
- Generate load (for example with `ab` or `hey`) and watch instance count rise; stop load and watch it fall.
**Interview Q:** What happens when an instance fails its health check?

---

### Phase 10 — CloudFront and HTTPS
**Goal:** Fast, secure global delivery.

**Steps**
1. Request an ACM certificate (in `us-east-1` for CloudFront) if using a custom domain.
2. CloudFront distribution with the ALB as origin for dynamic pages.
3. Second origin: S3 media bucket via Origin Access Control (bucket stays private).
4. Cache behaviours: cache media and static aggressively; do not cache dynamic pages or forward cookies/CSRF headers needed by Django.
5. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the CloudFront domain.
6. Optional: Route 53 record for your domain.

**Concepts:** CDN, edge locations, origins, cache behaviours, TLS certificates, OAC.
**Test:** Site loads over HTTPS; images come through CloudFront; login and forms still work (CSRF).
**Interview Q:** What should and should not be cached for a Django app?

---

## Part C — Make it stand out (Phases 11–13)

### Phase 11 — Lambda and serverless analytics (stage 2)
**Goal:** Move analytics to event-driven serverless services and add image alt-text.

**Steps**
1. DynamoDB table `PostCounters` (see `DATABASE.md`).
2. Lambda "record-view" behind API Gateway: increments the view counter with de-duplication (TTL on dedup items).
3. Small JavaScript on the post page calls the API.
4. EventBridge schedule (hourly) triggers "compute-trending" Lambda that writes top post ids/scores.
5. Django's Trending section reads those results.
6. Stretch: S3-upload-triggered Lambda calls Bedrock to produce image alt-text and stores it.
7. Give each Lambda its own least-privilege IAM role.

**Concepts:** event-driven architecture, API Gateway, DynamoDB key design, TTL, EventBridge schedules, Lambda permissions.
**Test:** Views increase in DynamoDB; Trending page matches the computed scores; Lambda logs appear in CloudWatch.
**Interview Q:** Why use DynamoDB for counters instead of RDS?

---

### Phase 12 — Infrastructure as code
**Goal:** Recreate the entire environment from code.

**Steps**
1. Choose Terraform or CloudFormation.
2. Write code in this order: network → security groups → RDS → S3 → IAM → launch template/ALB/ASG → CloudFront → Lambda.
3. Keep state/secrets out of Git.
4. Destroy and recreate the stack to prove it works.

**Concepts:** declarative infrastructure, state, drift, modules/stacks.
**Test:** One command creates the environment; one command removes it.
**Interview Q:** What problem does IaC solve compared with clicking in the console?

---

### Phase 13 — CI/CD, monitoring, final documentation
**Goal:** Automated testing/deployment and visibility.

**Steps**
1. GitHub Actions workflow: install dependencies, run `python manage.py test`, and deploy on success (for example by refreshing the Auto Scaling group with a new launch template version).
2. CloudWatch alarms: high CPU, ALB 5xx errors, unhealthy hosts, RDS connections; SNS email notification.
3. CloudWatch dashboard and application logs.
4. Final README: architecture diagram, screenshots, how to run, what is new.
5. Prepare a 5-minute demo and a viva question list.
6. Run the teardown checklist in `TASKS.md`.

**Concepts:** CI/CD, alarms, SNS, observability.
**Test:** A push triggers tests; breaking a test blocks deployment; a stopped instance triggers an alarm.
**Interview Q:** How do you know your app is healthy in production?

---

## Honest resume guide
Add a technology to your resume only after its phase is built and tested **and** you can answer its interview questions.

| After phase | You can honestly list |
|---|---|
| 2 | Django, authentication, CRUD |
| 5 | Amazon Bedrock integration, prompt design, boto3 |
| 8 | Amazon RDS, S3, IAM roles |
| 9 | EC2, Application Load Balancer, Auto Scaling |
| 10 | CloudFront, HTTPS/ACM |
| 11 | Lambda, API Gateway, DynamoDB, EventBridge |
| 12 | Terraform or CloudFormation |
| 13 | GitHub Actions CI/CD, CloudWatch |