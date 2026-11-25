# Cloud Architecture Specification

## 1. Current Deployed Architecture (Single-Instance Production)

The live production deployment on AWS (`ap-southeast-2` Sydney) is structured as follows:

```
                          Users (Web Browser)
                                   |
                             (HTTP Port 80)
                                   v
             +---------------------------------------------+
             |         AWS EC2 Instance (t3.micro)         |
             |           (Amazon Linux 2023)               |
             |                                             |
             |   [ Nginx 1.24 (Reverse Proxy / Web Server) ]|
             |                         |                   |
             |              (Unix Domain Socket)           |
             |                         v                   |
             |             [ Gunicorn 23.0 WSGI ]          |
             |                         |                   |
             |                         v                   |
             |               [ Django 5.2 App ]            |
             |             (WhiteNoise for Static)         |
             |                                             |
             |    [ EC2 IAM Role: EC2-Django-App-Role ]     |
             +---------------------+-----------------------+
                                   |
         +-------------------------+-------------------------+
         | (Port 5432, Private SG) | (SigV4, IAM Profile)    | (boto3, IAM Profile)
         v                         v                         v
  [ Amazon RDS ]            [ Amazon S3 ]             [ Amazon Bedrock ]
PostgreSQL 16 Engine     Bucket: aws-django-blog-    Nova Lite Model:
  (db.t4g.micro)            media-20261119           amazon.nova-lite-v1:0
Private Database Subnet   (Block Public Access ON)   (Sydney ap-southeast-2)
```

---

## 2. Planned Scale-Out Architecture (Future Milestone)

When horizontal scaling and multi-AZ high availability are required, the infrastructure expands into:

```
                          Users (Web Browser)
                                   |
                       [ Route 53 DNS ]               [Planned]
                                   |
                   [ CloudFront CDN + ACM HTTPS ]      [Planned]
                                   |
                [ Application Load Balancer (ALB) ]   [Planned]
                    (Public Subnets across 2 AZs)
                                   |
                +------------------+------------------+
                |                                     |
        [ EC2 App Server 1 ]                  [ EC2 App Server 2 ]   [Planned ASG]
        (Private Subnet AZ-A)                 (Private Subnet AZ-B)
                |                                     |
                +------------------+------------------+
                                   |
         +-------------------------+-------------------------+
         v                                                   v
  [ Amazon RDS Multi-AZ ]                             [ Amazon S3 ]
(Primary AZ-A, Standby AZ-B)                        (Media Object Storage)
                                                             |
                                                       (S3 Event)
                                                             v
                                                      [ AWS Lambda ] [Planned]
                                                  (Async Analytics Ingest)
```

---

## 3. Infrastructure Components

| Component | Status | Role & Configuration | Why We Use It |
|---|---|---|---|
| **VPC & Subnets** | **Deployed** | Custom VPC in `ap-southeast-2` with isolated subnets across 2 AZs. | Fenced private cloud perimeter separating public services from databases. |
| **Security Groups** | **Deployed** | EC2 SG allows 80/443; RDS SG allows 5432 *strictly* from EC2 SG. | Stateful firewalls implementing least-privilege traffic filtering. |
| **EC2 Instance** | **Deployed** | Amazon Linux 2023 running Nginx + Gunicorn WSGI. | Host application environment with native systemd process supervision. |
| **Nginx** | **Deployed** | Reverse proxy handling HTTP requests, buffering, and Unix sockets. | Efficiently buffers slow clients, terminates connections, and routes to WSGI. |
| **Gunicorn** | **Deployed** | Pre-fork WSGI HTTP worker pool (`3` workers). | Manages Python/Django processes and concurrent request handling. |
| **WhiteNoise** | **Deployed** | Serves compressed, cache-busted static files directly from Django. | Eliminates static file complexity on S3 for single-instance tiers. |
| **Amazon RDS** | **Deployed** | PostgreSQL 16 on `db.t4g.micro`, automated daily snapshots. | Managed database with automatic patching, backups, and point-in-time restore. |
| **Amazon S3** | **Deployed** | Bucket `aws-django-blog-media-20261119`, Block Public Access ON. | Highly durable, limitless cloud object storage for post hero images. |
| **EC2 IAM Role** | **Deployed** | `EC2-Django-App-Role` with policies for S3 and Bedrock `InvokeModel`. | Zero hardcoded API keys; temporary credentials rotated automatically via STS. |
| **Amazon Bedrock** | **Demo / Code Ready** | Amazon Nova Lite (`amazon.nova-lite-v1:0`) in Sydney. | Serverless foundation model for writing assistance without managing GPU servers. |
| **App Load Balancer** | **Planned** | Internet-facing ALB with health checks on `/health/`. | Evenly distributes traffic across multiple EC2 targets across availability zones. |
| **Auto Scaling Group**| **Planned** | Dynamic scaling policy based on CPU utilization and request count. | Automatically adds or terminates EC2 instances in response to traffic spikes. |
| **CloudFront & ACM** | **Planned** | Global edge distribution with free ACM TLS/SSL certificate. | Low-latency caching of static/media content and SSL offloading. |
| **AWS Lambda** | **Planned** | Serverless event workers for asynchronous analytics aggregation. | Offloads high-frequency view count batching from the relational database. |

---

## 4. Key Data Flows

### A. Publishing a Post with Hero Image
1. Author submits form containing text and uploaded image file.
2. Nginx buffers payload and passes request to Gunicorn over Unix socket.
3. Django's `CreatePostView` validates form fields and image dimensions via Pillow.
4. `django-storages` streams the image directly to Amazon S3 bucket `aws-django-blog-media-20261119`.
5. Django commits post record and S3 file path to Amazon RDS PostgreSQL.
6. Execution latency timer reports combined time (e.g., RDS: 14 ms, S3: 110 ms) in user toast.

### B. In-Editor AI Suggestion Generation
1. Author inputs draft title and body, then clicks **Suggest with AI**.
2. Client sends AJAX POST request to `/api/ai-suggestions/`.
3. `ai_assist/services.py` constructs a system prompt with formatting rules and 4 distinct style constraints.
4. If `AI_MOCK_MODE=false`, service invokes Amazon Bedrock Runtime via `boto3` (`InvokeModel` on `amazon.nova-lite-v1:0`).
5. If `AI_MOCK_MODE=true` (or Bedrock unreachable), intelligent mock AI parser extracts high-intent keywords and generates suggestions locally.
6. Cleaned JSON payload `{titles: [...], hashtags: [...], summary: "..."}` returns to editor.

### C. Trending Score Calculation & Privacy-Preserving View Tracking
1. Reader views post detail page `/post/<slug>/`.
2. `analytics/services.py` calculates SHA-256 hash of `visitor_ip + user_agent + salt`.
3. If no view exists for that hash within 30 minutes, a `PostView` record is created.
4. Hacker News gravity formula calculates decayed score:
   $$\text{Score} = \frac{\text{views} + (3 \times \text{likes}) + (5 \times \text{comments})}{(\text{age\_hours} + 2)^{1.5}}$$
5. Top 10 posts and relative rank changes are cached in memory for 30 seconds.

---

## 5. Security & Isolation Model

- **Zero Hardcoded Credentials**: No AWS access keys or secret keys exist in the repository or server filesystem. The EC2 instance assumes an IAM Instance Profile authenticated through IMDSv2.
- **Network Isolation**: The RDS PostgreSQL instance has no public IP address and resides in private database subnets. Its security group permits ingress on port 5432 *only* from the EC2 security group.
- **S3 Bucket Security**: Block Public Access is strictly enabled on the S3 bucket. Media files are accessed using presigned URLs or private authenticated requests.
- **Application Hardening**: In production, `DEBUG=False`, security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`) are enforced, and cookies are configured for HTTPS.
