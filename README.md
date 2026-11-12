# AWS Django Blog — Scalable Blog Platform with AI Suggestions and Trending Analytics

A cloud-hosted blog application built with **Django (Python)** and deployed on **AWS**.
Authors write posts, readers comment, and the platform adds two things beyond a plain blog:

1. **Trending analytics** — ranks posts by recent views, likes and comments.
2. **AI writing assistant (Amazon Bedrock)** — suggests titles, hashtags and a summary while an author is writing.

## Features
- User registration, login, logout
- Create / edit / delete posts (author only)
- Comments on posts
- Image upload for posts (S3 in production)
- Trending posts section (score-based, time-decayed)
- AI suggestions: titles, hashtags, one-line summary
- Scalable, secure deployment on AWS

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Django, Python |
| Database | Amazon RDS (MySQL or PostgreSQL); SQLite locally |
| Media | Amazon S3 |
| Hosting | EC2 + Auto Scaling behind an Application Load Balancer |
| CDN / HTTPS | CloudFront + ACM |
| Serverless | AWS Lambda (+ API Gateway, DynamoDB for analytics upgrade) |
| AI | Amazon Bedrock |
| Monitoring | CloudWatch |

## Project Structure (target)
```
aws-django-blog/
├── config/            # Django project settings, urls, wsgi
├── blog/              # posts, comments, tags, views, templates
├── analytics/         # view tracking + trending score
├── ai_assist/         # Bedrock suggestion service
├── templates/ static/ media/
├── lambda/            # Lambda function code (later phases)
├── infra/             # Terraform or CloudFormation (later phases)
├── docs/              # PRD, architecture, database, tasks, learning log
├── .agents/           # Antigravity rules and workflows
├── AGENTS.md
├── requirements.txt
└── manage.py
```

## Run Locally
```bash
python -m venv venv
# Windows PowerShell: venv\Scripts\Activate.ps1   |   Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000

## Documentation
- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database design](docs/DATABASE.md)
- [Build plan and status](docs/TASKS.md)
- [Learning log (interview prep)](docs/LEARNING_LOG.md)

## Status
See `docs/TASKS.md` for the current phase.

## Author
Swathi — B.Tech IT, MVSR Engineering College
