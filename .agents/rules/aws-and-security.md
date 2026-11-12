# AWS and security rules

## Security
- Security group chain: Internet -> ALB (80/443) -> EC2 (app port, source = ALB SG only) -> RDS (DB port, source = EC2 SG only).
- RDS in private subnets, not publicly accessible.
- EC2 reaches S3 and Bedrock through an **IAM role** with least-privilege policies. No `FullAccess` policies in the final design (allowed only temporarily while learning, and flagged for replacement).
- Store DB password and Django `SECRET_KEY` in environment variables or AWS Secrets Manager. Set `DEBUG=False` and a correct `ALLOWED_HOSTS` in production.
- S3 media bucket: block public access; serve through CloudFront where possible.
- Use HTTPS (ACM certificate). Note: ACM certificates used by CloudFront must be created in `us-east-1`.

## Cost safety
- Prefer free-tier-eligible sizes (e.g. `t2.micro` / `t3.micro`, `db.t3.micro`). Check the current free-tier terms before creating resources.
- NAT Gateways, ALBs, RDS and idle EC2 cost money. Tell Swathi before creating them.
- Create an AWS Budget alert on day one.
- At the end of every work session, remind Swathi which paid resources are still running. Provide a teardown checklist in `docs/TASKS.md`.

## Region
- Keep all resources in one region, except CloudFront-related ACM certificates (us-east-1).
- Before choosing the region, verify the chosen Bedrock model is available and enabled in that region.

## Bedrock usage
- Always return structured JSON from the model and validate it before using it.
- Handle errors, timeouts and throttling gracefully; the blog editor must still work if Bedrock fails.
- Limit input length and add a simple per-user rate limit to control cost.
- AI output is a suggestion only; the author always reviews and edits before publishing.
