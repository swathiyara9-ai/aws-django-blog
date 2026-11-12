# Build Plan and Status

Rule: work one phase at a time. Tick boxes only after testing. After each phase, update `LEARNING_LOG.md`.

## Open decisions
- [ ] Infrastructure as code tool: Terraform or CloudFormation
- [ ] Database engine on RDS: MySQL or PostgreSQL
- [ ] AWS region (check Bedrock model availability first)
- [ ] Bedrock model to use

## Phase 0 — Local setup
- [ ] Python 3.10+ installed, virtual environment created
- [ ] Django installed, project `config` and app `blog` created
- [ ] `python manage.py runserver` shows the Django welcome page
- [ ] Git repository initialised, `.gitignore` added, first commit
Done when: the welcome page opens at http://127.0.0.1:8000

## Phase 1 — Models and admin
- [ ] Models: Tag, Post, Comment, Like (see `DATABASE.md`)
- [ ] Migrations created and applied
- [ ] Models registered in admin; superuser created
Done when: you can create a Post with tags from the admin panel.

## Phase 2 — Authentication and post CRUD
- [ ] Base template with Bootstrap and navbar
- [ ] Register, login, logout pages
- [ ] Post list (paginated) and detail pages
- [ ] Create, edit, delete post (author only)
Done when: a new user can register, write, edit and delete their own post, and cannot edit others' posts.

## Phase 3 — Comments, likes, images
- [ ] Comment form on post detail
- [ ] Like / unlike button
- [ ] Image upload (local `media/`)
- [ ] Tag filter page
Done when: images show on posts and comments and likes work.

## Phase 4 — Trending analytics (stage 1, local)
- [ ] `analytics` app with PostView and PostStats
- [ ] Record view on post detail (with simple de-duplication)
- [ ] Score calculation service and management command `compute_trending`
- [ ] Trending section on home page
Done when: opening, liking and commenting on posts changes the Trending order after running the command.

## Phase 5 — AI suggestions (Bedrock)
- [ ] `ai_assist` app with `services.py`
- [ ] AWS credentials configured locally; Bedrock model access confirmed
- [ ] Endpoint returns JSON {titles, hashtags, summary}
- [ ] "Suggest" button in editor; author can apply or ignore each suggestion
- [ ] Error handling, input length limit, simple rate limit
Done when: clicking Suggest fills the editor options, and the editor still works if Bedrock is unreachable.

## Phase 6 — Production readiness
- [ ] Settings split by environment variables (`DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, DB, bucket, `BEDROCK_MODEL_ID`)
- [ ] Gunicorn, WhiteNoise or S3 for static files
- [ ] `requirements.txt` pinned; `collectstatic` works
- [ ] Health check URL `/health/`
Done when: the app runs locally in production-like mode with `DEBUG=False`.

## Phase 7 — AWS networking and safety
- [ ] AWS Budget alert created
- [ ] VPC, public and private subnets in 2 AZs, internet gateway, route tables
- [ ] Security groups: ALB, EC2, RDS
- [ ] S3 VPC gateway endpoint
Done when: network diagram matches `ARCHITECTURE.md`.

## Phase 8 — RDS and S3
- [ ] RDS instance in private subnets
- [ ] Django connects to RDS (from a test EC2 instance)
- [ ] S3 media bucket with block public access; django-storages configured
- [ ] IAM role for EC2 (least privilege)
Done when: posts and images save to RDS and S3 from an EC2 test instance.

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
