# Product Requirements Document (PRD)

## 1. Goal
Build a scalable, secure and reliable blog application on AWS using Django, and extend it with trending analytics and AI writing suggestions.

## 2. What is new in this project
Many public AWS capstones deploy a Django blog behind an ALB with Auto Scaling, RDS, S3, CloudFront and Lambda. This project keeps that solid base and adds:
1. **Trending analytics** — a score from views, likes and comments with time decay, shown as a Trending section.
2. **AI writing assistant (Bedrock)** — suggests titles, hashtags and a summary while the author writes.
3. **AI-assisted image alt-text and comment moderation** (optional stretch, via S3-triggered / event Lambda).
4. **Infrastructure as code** for repeatable deployment (Terraform or CloudFormation).

## 3. Users
- **Visitor**: reads posts, sees trending posts.
- **Registered user / author**: writes, edits, deletes own posts; comments; uses AI suggestions.
- **Admin**: manages all content through Django admin.

## 4. Functional requirements
| ID | Requirement | Priority |
|---|---|---|
| F1 | Register, log in, log out | Must |
| F2 | Create, edit, delete own posts | Must |
| F3 | Post list (paginated) and post detail pages | Must |
| F4 | Comments on posts (logged-in users) | Must |
| F5 | Upload one image per post | Must |
| F6 | Tags/hashtags on posts, click a tag to filter | Should |
| F7 | Track post views (one per visitor per post per time window) | Must |
| F8 | Likes on posts | Should |
| F9 | Trending section ranked by score | Must |
| F10 | "Suggest" button in editor returns 3-5 titles, 5-8 hashtags, one-line summary | Must |
| F11 | Author can accept, edit or ignore each suggestion | Must |
| F12 | Image alt-text auto-generated on upload (Lambda + Bedrock) | Could |
| F13 | Comment moderation check before publishing | Could |

## 5. Trending score (initial formula)
```
score = (views + 3*comments + 2*likes) / (hours_since_published + 2) ^ 1.5
```
Recalculated hourly. The formula is configurable and documented so it can be explained in a review.

## 6. Non-functional requirements
- **Scalability**: Auto Scaling group across two Availability Zones behind an ALB.
- **Security**: private DB, security-group chain, IAM roles, HTTPS, no secrets in code.
- **Reliability**: health checks, multi-AZ placement, blog works even if Bedrock is down.
- **Performance**: static and media content via CloudFront.
- **Cost**: free-tier-friendly sizes, budget alert, teardown checklist.
- **Observability**: CloudWatch logs, metrics and alarms.

## 7. Out of scope
Mobile app, real-time notifications, payments, multi-language support, full-text search.

## 8. Success criteria
- All "Must" requirements work locally and on AWS.
- App stays available when one instance is terminated.
- Trending page changes when posts get views and comments.
- AI suggestions appear in the editor and can be applied.
- Swathi can explain every component and its role in a viva or interview.
