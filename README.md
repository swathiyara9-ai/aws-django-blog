# AWS Django Blog — Scalable Cloud Blog Platform with AI Suggestions & Trending Analytics

[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20RDS%20%7C%20S3%20%7C%20Bedrock-232F3E?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Tests-63%20passed-success)](#testing)

A modern, cloud-hosted blogging platform developed by **Swathi** (3rd-year B.Tech IT, MVSR Engineering College). Built with **Django 5.2** and deployed on **Amazon Web Services (AWS)** using production-grade cloud architectural patterns.

Beyond standard CRUD blogging, this platform features two original innovations:
1. **Trending Post Analytics Engine**: A time-decay scoring algorithm with privacy-preserving visitor hashing that surfaces hot discussions.
2. **AI Writing Assistant (Amazon Bedrock Nova Lite)**: Serverless generative AI suggestions for titles, hashtags, and summaries directly in the post editor.
3. **Live Cloud Telemetry & Latency Profiling**: Real-time instrumentation tracking sub-millisecond execution times across Django, RDS, S3, and Bedrock.

---

## What Is New & Original

### 1. Trending Analytics with Time Decay
Traditional blogs sort posts purely by chronological order. This platform implements a mathematical ranking algorithm inspired by the Hacker News gravity model:

$$\text{Score} = \frac{\text{views} + (3 \times \text{likes}) + (5 \times \text{comments})}{(\text{age\_hours} + 2)^{1.5}}$$

- **Privacy-Preserving View Tracking**: Views are recorded only once every 30 minutes per visitor using an anonymised SHA-256 hash of `IP Address + User Agent`. No raw IP addresses or personally identifiable cookies are stored in the database.
- **Dynamic Rank Tracking**: Tracks previous vs. current rank positions (showing green up-arrows, red down-arrows, or fire badges for top posts).
- **Fast In-Memory Caching**: Top trending posts are cached in Django's cache layer with a 30-second TTL to avoid database strain under traffic surges.

### 2. AI Writing Assistant (Amazon Bedrock Nova Lite)
An in-editor writing copilot powered by Amazon Bedrock using **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) in the Sydney region (`ap-southeast-2`):
- **4 Distinct Title Options**: Produces diverse phrasing styles: *Statement*, *Question*, *Headline*, and *Story*.
- **Interactive Hashtag Chips**: Suggests high-intent tags that seamlessly integrate into the tag chip input with live database autocomplete (`/api/tags/?q=`).
- **One-Sentence Summary**: Generates concise meta-descriptions for social sharing.
- **Fail-Safe Offline Mode**: Built-in mock AI fallback generates intelligent context-aware suggestions locally when AWS Bedrock credentials are not present, ensuring zero downtime for authors.

### 3. Live Cloud Activity & Latency Telemetry
Every database query, media upload, and AI invocation is instrumented with microsecond timers:
- Real latency metrics are displayed in a non-intrusive toast after saving posts (e.g. `Post saved — RDS 14 ms, S3 120 ms`).
- A dedicated **Cloud Activity** telemetry dashboard displays live pipeline execution events and service latency breakdowns.

---

## Honest Implementation Status

In accordance with academic integrity and engineering honesty, here is the exact verification status of every component:

| Component / Feature | Implementation Status | Notes |
|---|---|---|
| **User Authentication & Profiles** | ✅ Built & Tested | Django auth, password change, session management. |
| **Post CRUD & Comments** | ✅ Built & Tested | Markdown/plain text, Pillow image sizing, cascade deletion. |
| **Hashtag Chip Input & Normalisation** | ✅ Built & Tested | Client chip UI, autocomplete API, server regex normalisation. |
| **4-Column Masonry Feed** | ✅ Built & Tested | 16-post batches, dynamic breakpoint rebalancing, bfcache restore. |
| **Trending Scoring & De-duplication** | ✅ Built & Tested | Time-decay formula, SHA-256 IP hashing, 30-min window. |
| **Cloud Activity Telemetry** | ✅ Built & Tested | Real execution timing (DB, S3, Django, AI), single toast queue. |
| **Dark / Light Theme System** | ✅ Built & Tested | Zero-flash head script, WCAG AA contrast, localStorage persistence. |
| **EC2 Linux Hosting** | 🚀 Deployed on AWS | Amazon Linux 2023, Gunicorn WSGI, Nginx reverse proxy. |
| **Amazon RDS Database** | 🚀 Deployed on AWS | PostgreSQL instance in private subnet (SQLite locally). |
| **Amazon S3 Media Storage** | 🚀 Deployed on AWS | `aws-django-blog-media-20261119` via django-storages & IAM Role. |
| **Amazon Bedrock AI** | 🧪 Demo Mode + Code Ready | Production boto3 code written & IAM scoped; tested in Mock/Demo mode. |
| **Application Load Balancer (ALB)** | 📋 Planned (Future Work) | Architecture designed; single EC2 used currently to minimise cost. |
| **EC2 Auto Scaling Group (ASG)** | 📋 Planned (Future Work) | Launch template prepared; not active on single-instance tier. |
| **CloudFront CDN & Custom Domain** | 📋 Planned (Future Work) | Static served via WhiteNoise; CloudFront planned for scale. |
| **AWS Lambda Async Counters** | 📋 Planned (Future Work) | Stage 2 serverless analytics planned for high-volume ingest. |

---

## Cloud Architecture

```mermaid
flowchart TD
    subgraph Client["Users & Client Tier"]
        Browser["Web Browser (Desktop / Mobile)"]
    end

    subgraph AWS["Amazon Web Services (ap-southeast-2 Sydney)"]
        subgraph PublicSubnet["Public Subnet"]
            Nginx["Nginx Web Server (Reverse Proxy, Port 80/443)"]
            Static["WhiteNoise (Static CSS/JS Assets)"]
        end

        subgraph Compute["App Server (EC2 Amazon Linux 2023)"]
            Gunicorn["Gunicorn WSGI Server"]
            Django["Django 5.2 Application"]
            IAM["EC2 IAM Instance Profile (Least Privilege)"]
        end

        subgraph PrivateSubnet["Private Database Subnet"]
            RDS[("Amazon RDS PostgreSQL (Port 5432)")]
        end

        subgraph CloudStorage["Cloud Managed Services"]
            S3[("Amazon S3 Media Bucket\n(aws-django-blog-media-20261119)")]
            Bedrock["Amazon Bedrock Runtime\n(Nova Lite: amazon.nova-lite-v1:0)"]
        end
    end

    subgraph Planned["Planned Scale-Out Architecture"]
        ALB["[Planned] Application Load Balancer"]
        ASG["[Planned] Auto Scaling Group"]
        CF["[Planned] CloudFront CDN + ACM SSL"]
        Lambda["[Planned] AWS Lambda Analytics Ingest"]
    end

    Browser -->|HTTP Requests| Nginx
    Nginx -->|Proxy Pass (Unix Socket)| Gunicorn
    Gunicorn --> Django
    Django -->|Reads/Writes Data| RDS
    Django -->|Uploads Post Images via IAM Role| S3
    Django -->|Invokes Generative AI via IAM Role| Bedrock
    IAM -.->|Grants Permissions| S3
    IAM -.->|bedrock:InvokeModel| Bedrock

    classDef planned fill:#f9f9f9,stroke:#999,stroke-dasharray: 5 5;
    class ALB,ASG,CF,Lambda planned;
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.10+, Django 5.2 | Core web framework, ORM, CBVs, Authentication |
| **WSGI / Web Server** | Gunicorn 23.0, Nginx | Production application server & reverse proxy |
| **Frontend & UI** | HTML5, Bootstrap 5.3, Bootstrap Icons | Responsive UI, 4-column masonry grid, dark mode |
| **Database** | PostgreSQL (AWS RDS), SQLite (local dev) | Relational database storage |
| **Media Storage** | Amazon S3 (django-storages, boto3) | Scalable object storage for user-uploaded post covers |
| **Static Assets** | WhiteNoise 6.9 | High-performance direct static file serving with gzip/brotli |
| **Generative AI** | Amazon Bedrock (Nova Lite `ap-southeast-2`) | AI title, hashtag, and summary generation |
| **Testing** | Django TestCase, RequestFactory | 63 automated tests verifying all core workflows |

---

## Project Structure

```
aws-django-blog/
├── config/                  # Django project configuration
│   ├── settings.py          # Environment-driven settings (DB, S3, Bedrock, Security)
│   ├── urls.py              # Root URL routing & API endpoints
│   ├── wsgi.py              # WSGI entry point for Gunicorn
│   └── asgi.py              # ASGI entry point
├── blog/                    # Core blog application
│   ├── models.py            # Post, Tag, Comment, Like models with Pillow aspect ratios
│   ├── views.py             # Feed, CRUD, masonry API, and telemetry views
│   ├── forms.py             # Post form with normalized hashtag chips
│   ├── urls.py              # Blog route definitions
│   └── management/commands/ # seed_demo management command
├── analytics/               # Trending analytics engine
│   ├── models.py            # PostView (SHA-256 hashed) and PostStats
│   ├── services.py          # Time-decay formula & rank tracking
│   └── utils.py             # Anonymised visitor hash calculation
├── ai_assist/               # Amazon Bedrock integration
│   ├── services.py          # Bedrock Nova Lite boto3 client & Mock AI engine
│   └── views.py             # AJAX AI suggestion endpoint
├── templates/               # Server-rendered HTML templates
│   ├── base.html            # Layout, dark-mode head script, toast container
│   └── blog/                # post_list, post_detail, post_form, architecture, trending
├── static/                  # CSS styles, JS feed scripts, SVG icons
├── docs/                    # Architectural & academic documentation
│   ├── ARCHITECTURE.md      # Cloud infrastructure specification
│   ├── DEPLOYMENT.md        # Step-by-step AWS EC2/RDS/S3 runbook
│   ├── DATABASE.md          # Relational schema diagrams & constraints
│   ├── TESTING.md           # Automated tests summary & manual test matrix
│   ├── VIVA.md              # 15 viva/interview questions & plain-English answers
│   ├── TASKS.md             # Completed development tasks checklist
│   └── LEARNING_LOG.md      # Detailed engineering logs & lessons learned
├── requirements.txt         # Pinned production Python dependencies
└── manage.py                # Django CLI management entry point
```

---

## How to Run Locally

### 1. Prerequisites
- Python 3.10 or newer
- Git

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/swathi/aws-django-blog.git
cd aws-django-blog

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the sample environment file:
```bash
cp .env.example .env
```
For local development, the defaults in `.env.example` work out of the box with SQLite and Mock AI mode.

### 4. Run Migrations & Seed Sample Data
```bash
python manage.py migrate

# Seed 12 sample users, posts, tags, comments, likes, and trending scores
python manage.py seed_demo --yes

# Create an administrator account
python manage.py createsuperuser
```

### 5. Start Development Server
```bash
python manage.py runserver
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## AWS Deployment Overview

The application is deployed on AWS following the Well-Architected Framework:

1. **Virtual Private Cloud (VPC)**: Custom VPC in `ap-southeast-2` (Sydney) with isolated public and private subnets across two Availability Zones.
2. **Compute (EC2)**: Amazon Linux 2023 instance running Nginx as a reverse proxy, forwarding requests over a local Unix domain socket to Gunicorn WSGI workers.
3. **Database (RDS)**: Amazon RDS PostgreSQL (db.t4g.micro) residing in private subnets, accepting connections strictly from the EC2 security group on port 5432.
4. **Media Storage (S3)**: S3 bucket `aws-django-blog-media-20261119` with **Block Public Access enabled**. Django generates time-limited SigV4 signed URLs for secure image viewing.
5. **Security & Permissions**: The EC2 instance accesses S3 and Bedrock via an **IAM Instance Profile** (`EC2-Django-App-Role`), eliminating the need for hardcoded AWS credentials.

*For complete step-by-step deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).*

---

## Environment Variables Reference

All runtime configuration is managed through environment variables via `python-dotenv`:

| Variable Name | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | Yes (in prod) | Django default (dev) | Cryptographic signing key for sessions & CSRF |
| `DEBUG` | No | `False` | Enables/disables debug mode (must be `False` in prod) |
| `ALLOWED_HOSTS` | Yes (in prod) | `127.0.0.1,localhost` | Comma-separated domain names / IP addresses |
| `CSRF_TRUSTED_ORIGINS` | No | `http://127.0.0.1:8000` | Origins permitted to perform state-changing POSTs |
| `DB_ENGINE` | No | SQLite (built-in) | Set to `django.db.backends.postgresql` for RDS |
| `DB_NAME` | No | `""` | RDS PostgreSQL database name |
| `DB_USER` | No | `""` | RDS PostgreSQL database username |
| `DB_PASSWORD` | No | `""` | RDS PostgreSQL database password |
| `DB_HOST` | No | `""` | RDS endpoint DNS hostname |
| `DB_PORT` | No | `5432` | Database port (5432 for Postgres) |
| `AWS_STORAGE_BUCKET_NAME`| No | Local `media/` folder | Amazon S3 bucket name for user media uploads |
| `AWS_S3_REGION_NAME` | No | `ap-southeast-2` | AWS region where S3 bucket resides |
| `AWS_REGION` | No | `ap-southeast-2` | AWS region for Amazon Bedrock Runtime calls |
| `BEDROCK_MODEL_ID` | No | `amazon.nova-lite-v1:0`| Amazon Bedrock foundation model ID |
| `AI_MOCK_MODE` | No | `true` | When `true`, uses intelligent offline mock AI |
| `SECURE_SSL_REDIRECT` | No | `False` | Redirects all HTTP traffic to HTTPS (enable with SSL) |
| `SESSION_COOKIE_SECURE` | No | `False` | Marks session cookies as HTTPS-only |
| `CSRF_COOKIE_SECURE` | No | `False` | Marks CSRF cookies as HTTPS-only |
| `SECURE_HSTS_SECONDS` | No | `0` | HTTP Strict Transport Security header duration |

---

## Testing

The codebase includes 63 automated unit tests covering every critical system component:
```bash
python manage.py test
```
```text
Found 63 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...............................................................
----------------------------------------------------------------------
Ran 63 tests in 6.541s

OK
Destroying test database for alias 'default'...
```

*For test breakdown and the complete manual testing matrix, see [docs/TESTING.md](docs/TESTING.md).*

---

## Screenshots

> *Placeholder: Add application screenshots before submission.*

| Responsive 4-Column Masonry Feed | AI Writing Assistant Modal |
|:---:|:---:|
| `![Feed Screenshot](docs/screenshots/feed.png)` | `![AI Suggestions Screenshot](docs/screenshots/ai_suggest.png)` |

| Live Cloud Activity Telemetry | Light / Dark Mode Comparison |
|:---:|:---:|
| `![Cloud Activity](docs/screenshots/cloud_activity.png)` | `![Dark Mode](docs/screenshots/dark_mode.png)` |

---

## Documentation Links
- [Architecture Deep-Dive](docs/ARCHITECTURE.md)
- [Production Deployment Runbook](docs/DEPLOYMENT.md)
- [Testing Summary & Manual Checklist](docs/TESTING.md)
- [Viva & Interview Questions](docs/VIVA.md)
- [Database Schema Design](docs/DATABASE.md)
- [Engineering Learning Log](docs/LEARNING_LOG.md)

---

## Author & Academic Acknowledgements
- **Author**: Swathi
- **Degree**: Bachelor of Technology in Information Technology (3rd Year)
- **Institution**: MVSR Engineering College, Hyderabad
- **Faculty Mentor**: Dept. of Information Technology
