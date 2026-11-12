# AGENTS.md — Project Identity and Working Agreement

## Project
AWS Django Blog: a Django blog app deployed on AWS (EC2, RDS, S3, ALB, Auto Scaling, CloudFront, Lambda) with two original features: **trending-post analytics** and **Amazon Bedrock title/hashtag/summary suggestions**.

Read before any task: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/TASKS.md`.

## About the developer
Swathi is a third-year B.Tech IT student. She is learning AWS and Django while building this. The project will be reviewed by a faculty mentor and discussed in interviews, so she must understand every part.

## How to work (most important)
1. **One phase at a time.** Work only on the current phase in `docs/TASKS.md`. Never jump ahead.
2. **Plan first.** Before writing code, state in plain words what you will build and which files you will touch. Wait for confirmation.
3. **Small steps.** Make small changes. After each step, give the exact command to run and what the result should look like.
4. **Explain while building.** For each new concept (model, view, migration, IAM role, security group, etc.) add a short, simple explanation: what it is, why we need it, how it connects to the rest. Use everyday analogies. No unexplained magic.
5. **Copy-paste ready.** Give full commands and full file contents, not fragments.
6. **Confirm before moving on.** At the end of each phase, summarise, list what to test, update `docs/TASKS.md` and `docs/LEARNING_LOG.md`, then ask whether to continue.
7. **Be honest.** If something is not working or you are unsure, say so. Do not claim a feature works without running it.

## Tech decisions
- Python 3.10+, latest stable Django. Pin versions in `requirements.txt`.
- Django built-in auth, ORM, admin, forms. Server-rendered templates with Bootstrap. No separate frontend framework.
- SQLite locally; MySQL or PostgreSQL on RDS. Settings must switch by environment variable.
- Media: local `media/` in development, S3 (django-storages) in production.
- AI: `boto3` Bedrock Runtime. Model id comes from the `BEDROCK_MODEL_ID` setting, never hard-coded in views.
- Infrastructure as code: Terraform or CloudFormation (decision pending, see TASKS.md).

## Do not
- Never commit secrets, `.env`, AWS keys, or `db.sqlite3`. Keep `.gitignore` updated.
- Never hard-code AWS credentials. Locally use `aws configure` / profiles; on EC2 use IAM roles.
- Never open security groups to `0.0.0.0/0` except the ALB on 80/443.
- Never create paid AWS resources without telling Swathi the cost impact first.
- Never run destructive commands (`terraform destroy`, deleting DBs/buckets) without explicit confirmation.
- Never list a technology in README or resume text unless it is actually built and working.

## Definition of done for any task
Runs locally without errors, has a manual test checklist, is explained in simple words, is logged in `docs/LEARNING_LOG.md`.
