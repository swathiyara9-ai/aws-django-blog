# AWS Production Deployment Runbook

This guide documents the exact, reproducible steps to deploy the Django blog application to an **Amazon EC2** instance running **Amazon Linux 2023**, backed by **Amazon RDS PostgreSQL** and **Amazon S3** in `ap-southeast-2` (Sydney).

> [!NOTE]
> All sensitive values (IP addresses, passwords, domain names, bucket names) are shown using placeholders. Replace them with your specific AWS resource values.

---

## 1. Prerequisites & AWS Infrastructure Setup

### A. AWS Region & VPC
- **Region**: `ap-southeast-2` (Sydney)
- **VPC**: 1 VPC with 2 Public Subnets and 2 Private Subnets across `ap-southeast-2a` and `ap-southeast-2b`.
- **Internet Gateway (IGW)** attached to VPC with default route `0.0.0.0/0` in public route tables.

### B. Security Groups
1. **EC2 Security Group (`blog-ec2-sg`)**:
   - Inbound: HTTP (TCP 80) from `0.0.0.0/0`
   - Inbound: HTTPS (TCP 443) from `0.0.0.0/0`
   - Inbound: SSH (TCP 22) from `<YOUR_ADMIN_IP>/32`
   - Outbound: All traffic (`0.0.0.0/0`)
2. **RDS Security Group (`blog-rds-sg`)**:
   - Inbound: PostgreSQL (TCP 5432) strictly from source `blog-ec2-sg` (Security Group ID)
   - Outbound: None required

### C. Amazon RDS PostgreSQL Instance
- **Engine**: PostgreSQL 16.x
- **Instance Type**: `db.t4g.micro`
- **Subnet Group**: Private database subnets (no public IP assigned)
- **Database Name**: `blogdb`
- **Master Username**: `dbadmin`
- **Master Password**: `<YOUR_STRONG_DB_PASSWORD>`
- **Security Group**: `blog-rds-sg`

### D. Amazon S3 Bucket & IAM Instance Profile
1. Create S3 Bucket: `aws-django-blog-media-<ACCOUNT_OR_SUFFIX>` in `ap-southeast-2`.
   - **Block Public Access**: Keep **ALL** options enabled (ON).
   - **Encryption**: SSE-S3 (default).
2. Create IAM Policy `DjangoAppS3AndBedrockPolicy`:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "S3MediaBucketAccess",
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::aws-django-blog-media-<ACCOUNT_OR_SUFFIX>",
           "arn:aws:s3:::aws-django-blog-media-<ACCOUNT_OR_SUFFIX>/*"
         ]
       },
       {
         "Sid": "BedrockNovaLiteInvoke",
         "Effect": "Allow",
         "Action": "bedrock:InvokeModel",
         "Resource": "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0"
       }
     ]
   }
   ```
3. Create IAM Role `EC2-Django-App-Role`, attach the policy, and attach this role to the EC2 instance as an **IAM Instance Profile**.

---

## 2. EC2 Server Provisioning

Launch an EC2 instance:
- **AMI**: Amazon Linux 2023 (64-bit x86 or ARM64)
- **Instance Type**: `t3.micro` (or `t4g.micro` if ARM)
- **Key Pair**: `<YOUR_SSH_KEY>.pem`
- **Security Group**: `blog-ec2-sg`
- **IAM Instance Profile**: `EC2-Django-App-Role`

SSH into the instance:
```bash
ssh -i /path/to/<YOUR_SSH_KEY>.pem ec2-user@<EC2_PUBLIC_IP>
```

### Install System Packages & Python 3.11
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git nginx libpq-devel gcc
```

---

## 3. Application Setup

### Clone Repository & Create Virtual Environment
```bash
cd /home/ec2-user
git clone https://github.com/<YOUR_GITHUB_USER>/aws-django-blog.git
cd aws-django-blog

python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Configure Production Environment Variables (`.env`)
Create `/home/ec2-user/aws-django-blog/.env`:
```ini
# Core Django
SECRET_KEY=<GENERATED_RANDOM_50_CHAR_KEY>
DEBUG=False
ALLOWED_HOSTS=<EC2_PUBLIC_IP>,<YOUR_DOMAIN_IF_ANY>,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://<EC2_PUBLIC_IP>

# RDS PostgreSQL Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=blogdb
DB_USER=dbadmin
DB_PASSWORD=<YOUR_STRONG_DB_PASSWORD>
DB_HOST=<YOUR_RDS_ENDPOINT>.ap-southeast-2.rds.amazonaws.com
DB_PORT=5432

# S3 Media Storage
AWS_STORAGE_BUCKET_NAME=aws-django-blog-media-<ACCOUNT_OR_SUFFIX>
AWS_S3_REGION_NAME=ap-southeast-2

# Amazon Bedrock
AWS_REGION=ap-southeast-2
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
AI_MOCK_MODE=false

# HTTPS Security (Enable when custom domain & SSL certificate exist)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
```

### Run Migrations, Collect Static & Create Admin
```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## 4. Gunicorn WSGI Configuration

Create systemd service file:
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Paste the following configuration:
```ini
[Unit]
Description=Gunicorn daemon for AWS Django Blog
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/aws-django-blog
ExecStart=/home/ec2-user/aws-django-blog/venv/bin/gunicorn \
    --access-logfile - \
    --error-logfile - \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    config.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start Gunicorn:
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

---

## 5. Nginx Reverse Proxy Configuration

Create Nginx site configuration:
```bash
sudo nano /etc/nginx/conf.d/django_blog.conf
```

Paste configuration:
```nginx
server {
    listen 80;
    server_name <EC2_PUBLIC_IP> <YOUR_DOMAIN_IF_ANY>;

    client_max_body_size 20M;

    # WhiteNoise serves static files directly from Django,
    # or optionally routed via Nginx:
    location /static/ {
        alias /home/ec2-user/aws-django-blog/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Test and restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 6. Verification Checklist

1. **Web Access**: Open `http://<EC2_PUBLIC_IP>/` in your browser. The 4-column feed should load.
2. **Health Check**: Open `http://<EC2_PUBLIC_IP>/health/`. Expected: `{"status": "ok", "db": "healthy"}` with HTTP 200.
3. **Admin Dashboard**: Open `http://<EC2_PUBLIC_IP>/admin/` and log in.
4. **Media Upload**: Create a post with an image. Verify the image appears and inspect the URL (should point to `https://aws-django-blog-media-...s3.ap-southeast-2.amazonaws.com/...`).
5. **Bedrock AI**: In post editor, click "Suggest with AI". Verify titles and hashtags return without errors.

---

## 7. Routine Update Runbook (Deployment Commands)

To deploy application updates without downtime:

```bash
cd /home/ec2-user/aws-django-blog
source venv/bin/activate

# 1. Pull latest code
git pull origin main

# 2. Update Python dependencies
pip install -r requirements.txt

# 3. Apply schema migrations
python manage.py migrate

# 4. Gather static assets
python manage.py collectstatic --noinput

# 5. Gracefully restart Gunicorn workers
sudo systemctl restart gunicorn

# 6. Verify health
curl -I http://127.0.0.1:8000/health/
```
