# Database Design

## Relational (Django ORM -> SQLite locally, RDS in AWS)

### User
Django built-in `auth.User` (username, email, password hash).

### Tag
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| name | CharField(50) | unique, stored lowercase without `#` |

### Post
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| author | ForeignKey(User) | on_delete=CASCADE |
| title | CharField(200) | |
| slug | SlugField | unique |
| body | TextField | |
| summary | CharField(300) | blank allowed; can be AI suggested |
| image | ImageField | upload_to='posts/', blank allowed |
| image_alt | CharField(255) | blank allowed; can be AI generated |
| tags | ManyToManyField(Tag) | blank allowed |
| status | CharField | draft / published |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

### Comment
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| post | ForeignKey(Post) | related_name='comments' |
| author | ForeignKey(User) | |
| body | TextField | |
| is_approved | BooleanField | default True; used by optional moderation |
| created_at | DateTimeField | auto_now_add |

### Like
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| post | ForeignKey(Post) | |
| user | ForeignKey(User) | |
| created_at | DateTimeField | |
Constraint: unique (post, user).

### PostView (analytics, stage 1)
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| post | ForeignKey(Post) | |
| user | ForeignKey(User, null) | null for anonymous |
| visitor_hash | CharField(64) | hash of IP + user-agent (never store raw IP) |
| viewed_at | DateTimeField | auto_now_add |

### PostStats (analytics, stage 1)
| Field | Type | Notes |
|---|---|---|
| post | OneToOneField(Post) | PK |
| views | IntegerField | |
| likes | IntegerField | |
| comments | IntegerField | |
| score | FloatField | trending score |
| updated_at | DateTimeField | |

## DynamoDB (analytics, stage 2 — AWS upgrade)
Table `PostCounters`
| Key | Example |
|---|---|
| pk (partition) | `post#42` |
| sk (sort) | `counter` or `dedup#<visitor_hash>` |
Attributes: `views`, `likes`, `comments`, `ttl` (for dedup rows).

## Relationships summary
- User 1—N Post, User 1—N Comment, User 1—N Like
- Post 1—N Comment, Post 1—N Like, Post N—N Tag
- Post 1—N PostView, Post 1—1 PostStats

## Indexes to add
- `Post.slug` (unique), `Post.created_at`, `PostView(post, viewed_at)`, `PostStats.score`.
