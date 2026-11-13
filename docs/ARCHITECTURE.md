# Architecture

## 1. High-level diagram
```
                         Users (Browser)
                               |
                          [ Route 53 ]  (optional custom domain)
                               |
                         [ CloudFront ]  <-- HTTPS (ACM cert, us-east-1)
                               |
                    [ Application Load Balancer ]   (public subnets, 2 AZs)
                               |
              +----------------+----------------+
              |                                 |
      [ EC2 - Django/Gunicorn ]       [ EC2 - Django/Gunicorn ]    <- Auto Scaling Group (private subnets)
              |        |                        |        |
              |        +------------+-----------+        |
              |                     |                    |
        [ Amazon RDS ]         [ Amazon S3 ]        [ Bedrock Runtime ]
        (private subnets)     (media + static)       (title/hashtag AI)
                                    |
                              (S3 event)
                                    v
                              [ AWS Lambda ] ---> [ Bedrock ] / [ DynamoDB ]

  CloudWatch: logs, metrics, alarms for all of the above
```

## 2. Components and why we use them
| Component | Role | Simple explanation |
|---|---|---|
| VPC | Private network for the project | Our own fenced compound inside AWS |
| Public subnets | Hold the ALB (and NAT if used) | The gate area facing the road |
| Private subnets | Hold EC2 app servers and RDS | Rooms inside the compound, no direct street access |
| Security groups | Firewalls per resource | Guards that only let in approved visitors |
| ALB | Spreads traffic across servers; health checks | A receptionist directing visitors to a free desk |
| EC2 + Launch Template | Runs the Django app | The workers; the template is their job description |
| Auto Scaling Group | Adds or removes EC2 based on load | Hires more workers when busy, sends them home when quiet |
| RDS | Managed relational database | A professionally managed filing room |
| S3 | Stores uploaded images (and static files) | Unlimited cloud cupboard |
| CloudFront | CDN and HTTPS front door | Local copy shops near readers worldwide |
| Lambda | Small event-driven functions | A helper who wakes up only when called |
| API Gateway + DynamoDB | Serverless event counting (analytics upgrade) | Fast tally counter that scales by itself |
| Bedrock | Generative AI suggestions via Amazon Nova Lite (ap-southeast-2) | The writing assistant |
| IAM roles | Permissions for EC2 and Lambda | An ID badge with limited access |
| CloudWatch | Logs, metrics, alarms | Security cameras and alarms |
| ACM | Free TLS certificates | The padlock on the website |

## 3. Key data flows
**A. Create a post with image**
Browser -> ALB -> Django -> saves text in RDS, image in S3 (via django-storages) -> page served; image URL goes through CloudFront.

**B. AI suggestions**
Editor "Suggest" click -> Django endpoint -> `ai_assist/services.py` -> Bedrock Runtime Converse API (Amazon Nova Lite `amazon.nova-lite-v1:0` in `ap-southeast-2`) -> JSON {titles, hashtags, summary} -> shown in editor; author chooses.

**C. View counting and trending (two stages)**
- Stage 1 (local, simple): Django records a `PostView` row; an hourly management command/cron computes scores into `PostStats`.
- Stage 2 (AWS upgrade): browser script -> API Gateway -> Lambda -> DynamoDB counters; EventBridge triggers an hourly Lambda that computes trending scores; Django reads the top posts.

**D. Image alt-text (stretch)**
S3 upload event -> Lambda -> Bedrock (describe image) -> writes alt-text back to the database or an S3 object tag.

## 4. Security design
- Security group chain: Internet -> ALB (80/443) -> EC2 (app port, from ALB SG only) -> RDS (3306/5432, from EC2 SG only).
- RDS not publicly accessible; EC2 in private subnets; outbound internet via NAT Gateway or VPC endpoints (see cost note).
- VPC Gateway Endpoint for S3 keeps S3 traffic off the public internet.
- IAM role on EC2: least-privilege access to the media bucket and `bedrock:InvokeModel` scoped strictly to `arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0`.
- Secrets in environment variables or Secrets Manager; `DEBUG=False` in production.

## 5. Cost notes (read before building)
- NAT Gateway, ALB, RDS and running EC2 instances can incur charges even when idle.
- Cheaper learning option: start with EC2 in public subnets with tight security groups, then move to private subnets once everything works.
- Set an AWS Budget alert first. Tear down resources after demos (checklist in `TASKS.md`).

## 6. Environments
| Setting | Local | AWS |
|---|---|---|
| DB | SQLite | RDS |
| Media | `media/` folder | S3 + CloudFront |
| Debug | True | False |
| AI | Your AWS profile credentials | EC2 IAM role |
