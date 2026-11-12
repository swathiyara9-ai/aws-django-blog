# Learning Log (interview and viva prep)

After every phase, add an entry. Keep answers in your own words.

## Template
### Phase N — Title (date)
**What I built:**
**New concepts:** (term — one-line meaning)
**Problems faced and fixes:**
**Likely questions and my answers:**
1. Q:
   A:
**Can I honestly put this on my resume?** yes / not yet (reason)

---

## Phase 0 — Local setup
**What I built:** Django project `config` and app `blog` running locally in a virtual environment.
**New concepts:**
- Virtual environment — private set of Python packages for one project.
- Django project vs app — project holds settings and routing; apps hold features.
- `manage.py` — command-line control panel for Django.
**Likely questions and my answers:**
1. Q: Why use a virtual environment?
   A: (write in your own words)


---

## Phase 1 — Models and admin (November 12, 2026)
**What I built:** Core database models (`Tag`, `Post`, `Comment`, `Like`) in Django ORM, created and applied migrations, and registered all models in the Django admin dashboard with search, filters, and auto-populated slugs.
**New concepts:**
- ORM (Object-Relational Mapping) — Translates Python model classes directly into database tables and SQL queries.
- Migration — A version-controlled Python script describing changes to database schema over time.
- ForeignKey — Creates a one-to-many relationship (e.g. one User has many Posts).
- ManyToManyField — Creates a many-to-many relationship using a bridge/junction table (e.g. Posts and Tags).
- UniqueConstraint — Enforces uniqueness at the database level across multiple columns (e.g. one Like per post per user).
- Django Admin — Built-in back-office UI for managing data models without writing custom admin views.
**Problems faced and fixes:**
- Need Pillow installed for `ImageField`: confirmed `pillow==12.2.0` is pinned in `requirements.txt`.
- Configured `MEDIA_URL` and `MEDIA_ROOT` in `settings.py` so uploaded images are stored neatly in `media/posts/`.
**Likely questions and my answers:**
1. Q: What is a migration and why shouldn't you edit the database schema directly?
   A: A migration is a version-controlled Python file that records changes made to models. Editing database tables directly bypasses version control, makes team collaboration and CI/CD impossible to reproduce, and can cause Django's model state and database schema to fall out of sync.
2. Q: What is the difference between ForeignKey and ManyToManyField in Django?
   A: A ForeignKey represents a one-to-many relationship (a Comment points to one Post, but a Post has many Comments). A ManyToManyField represents an N-to-N relationship (a Post can have multiple Tags, and a Tag can belong to multiple Posts) handled via a hidden junction table.
3. Q: How do you prevent a user from liking the same post multiple times?
   A: By defining a `UniqueConstraint(fields=['post', 'user'], name='unique_post_user_like')` in the `Like` model's `Meta` class, the database itself enforces that a given `(post, user)` pair can only exist once.
**Can I honestly put this on my resume?** Yes — Built relational data models in Django ORM with foreign keys, M2M relationships, and composite constraints, with a configured administrative backend.


---

## Phase 2 — Authentication and post CRUD (November 12, 2026)
**What I built:** User registration with automatic login, CSRF-protected authentication (login/logout), base Bootstrap 5 template with responsive navbar and dismissible alerts, full CRUD for posts via Class-Based Views (`ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`), slug collision handling, author authorization via mixins, draft isolation, and an 8-test automated suite.
**New concepts:**
- Class-Based Views (CBVs) — Object-oriented views (`ListView`, `CreateView`, etc.) that eliminate repetitive boilerplate for standard CRUD operations.
- Mixins — Composable classes (`LoginRequiredMixin`, `UserPassesTestMixin`) used to inject authentication and permission checks into views.
- CSRF Token — A cryptographic token included in state-changing requests (POST) to protect users from Cross-Site Request Forgery attacks.
- Template Inheritance — Reusable layout architecture where pages extend a parent template (`base.html`) and override specific content blocks.
- Authentication vs Authorization — Authentication verifies user identity (logging in); Authorization restricts actions based on permissions (author-only editing).
- Slug — A URL-friendly string derived from a title, providing human-readable, SEO-optimized web addresses.
**Problems faced and fixes:**
- Django 5 enforces POST requests for logout to prevent CSRF attacks: replaced plain link with a CSRF-protected form submit button in the navbar.
- Draft posts needed to remain visible to the author for previewing while remaining invisible to the public: filtered `PostDetailView` queryset with `Q(status='published') | Q(author=request.user)`.
**Likely questions and my answers:**
1. Q: What is the difference between Authentication and Authorization, and how did you implement them?
   A: Authentication verifies *who the user is* (handled by Django's `auth` views and `UserCreationForm`). Authorization determines *what the user is permitted to do* (enforced via `UserPassesTestMixin` on `PostUpdateView` and `PostDeleteView` to restrict edits and deletions strictly to the post's author, returning HTTP 403 to unauthorized users).
2. Q: Why use Class-Based Views (CBVs) instead of function-based views (FBVs)?
   A: CBVs encapsulate standard patterns like listing, pagination, form validation, and deletion into reusable classes. They allow clean code reuse through inheritance and mixins without rewriting boilerplate logic, while still offering granular hooks like `form_valid()` and `get_queryset()` when customization is needed.
3. Q: Why does Django 5 require logout to be a POST request instead of a simple GET link?
   A: Using GET requests for state-changing operations like logout makes the application vulnerable to Cross-Site Request Forgery (CSRF). A malicious website could trick a user's browser into visiting `/logout/` via an image tag or hidden link. Enforcing a POST request with a CSRF token ensures logouts are deliberate and originating from our trusted site.
**Can I honestly put this on my resume?** Yes — Implemented authentication, role-based authorization, and complete CRUD workflows using Django Class-Based Views, secured with CSRF protection and covered by unit tests.
