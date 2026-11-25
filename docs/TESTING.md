# Automated Testing & Manual Quality Assurance Guide

This document summarizes the automated test suite and provides a complete manual test checklist for verifying all features of the AWS Django Blog.

---

## 1. Automated Test Suite Summary

The application includes **63 automated unit and integration tests** written with Django's `TestCase` and `Client`.

Run tests with:
```bash
python manage.py test
```

### Test Coverage Breakdown

| Test Class | Module | Tests | Description |
|---|---|:---:|---|
| `AuthTests` | `blog.tests` | 6 | User registration, login, logout, password change, authenticated view access, and session integrity. |
| `PostCRUDTests` | `blog.tests` | 10 | Post creation, detail viewing, author-only editing, deletion, slug generation, collision handling, and draft visibility. |
| `CommentAndLikeTests` | `blog.tests` | 7 | Adding comments, newest-first ordering, liking/unliking posts, and duplicate like prevention via database unique constraint. |
| `TagTests` | `blog.tests` | 6 | Tag creation, reuse of existing tags, M2M post association, tag filter page, and `/api/tags/` autocomplete search. |
| `TagNormalizationTests`| `blog.tests` | 6 | Stripping `#`, whitespace trimming, lowercase conversion, regex character validation (`^[a-z0-9_]+$`), and 10-tag limit enforcement. |
| `FeedMasonryTests` | `blog.tests` | 6 | Server-rendered 16-post initial batch (noscript friendly), `/posts/feed/` 16-post batching, `has_more` flag, and `Cache-Control: no-store` header. |
| `TrendingAnalyticsTests`| `analytics.tests` | 8 | Post view recording, 30-minute visitor de-duplication via SHA-256 IP/User-Agent hashing, gravity score calculation, time decay, and top 10 cache. |
| `AIAssistTests` | `ai_assist.tests` | 6 | Bedrock Nova Lite payload structure, Mock AI fallback generation (4 title styles, hashtags, summary), prompt input sanitization, and rate limits. |
| `CloudActivityTests` | `blog.tests` | 4 | Real-time telemetry tracking (`ActivityEvent`), operation duration recording (Django, DB, S3, AI), and `/api/cloud-activity/` JSON API. |
| `UIAndNotificationTests`| `blog.tests` | 4 | Single toast notification container, suppression of duplicate toasts, favicon `/favicon.ico` route, and health check endpoint `/health/`. |

---

## 2. Comprehensive Manual Test Checklist

Use this checklist during manual review, demonstration, or viva presentation:

### Checklist 1: User Accounts & Authentication
- [ ] **Registration**: Navigate to `/register/`. Create a new user `alice`. Verify automatic login and redirect to home feed.
- [ ] **Logout**: Click the Logout button at the bottom of the sidebar. Verify user session terminates and navbar updates to "Login".
- [ ] **Login**: Log in as `alice`. Enter invalid password; verify user-friendly error message. Enter correct password; verify success.
- [ ] **Settings & Password Change**: Navigate to `/settings/`. Change password via Django's `PasswordChangeView`. Verify session remains active without unexpected logout.

### Checklist 2: 4-Column Responsive Feed & Endless Scroll
- [ ] **Server-Rendered Initial Batch**: Disable JavaScript in DevTools and refresh `/`. Verify the first 16 post cards are present in the server HTML.
- [ ] **4-Column Desktop Layout**: On a screen $\ge 1200\text{px}$, verify post cards distribute across 4 equal-width masonry columns.
- [ ] **Responsive Breakpoints**:
  - Resize browser to 900px–1199px: verify layout cleanly adjusts to 3 columns without page reload.
  - Resize to 576px–899px: verify 2 columns.
  - Resize below 576px: verify single-column layout.
- [ ] **Infinite Scroll**: Enable JavaScript. Scroll to the bottom of the page. Verify the skeleton loader displays briefly, and the next 16 posts load and append to the shortest column.
- [ ] **All Caught Up**: Scroll through all posts until the end. Verify the "You're all caught up!" banner appears.

### Checklist 3: Post Creation, Hashtags & Editing
- [ ] **Create Post**: Click the `+` button in the sidebar. Fill in title, body, and select a cover image.
- [ ] **Hashtag Chip Input**:
  - Type `django` and press <kbd>Enter</kbd>. Verify it converts into a badge `#django` with an `×` button.
  - Type `#aws,` (with comma). Verify `#` is stripped and `#aws` chip appears.
  - Click `×` on a chip. Verify the chip is removed.
  - Type `a` to see autocomplete dropdown from `/api/tags/?q=a`. Click a suggestion to add.
  - Attempt to add more than 10 tags. Verify client blocks additional tags.
- [ ] **AI Suggestions**:
  - Click **Suggest with AI**.
  - Verify 4 distinct title styles appear (Statement, Question, Headline, Story).
  - Click one suggested title; verify it populates the title input.
  - Click suggested hashtag chips; verify they toggle into the tag input.
- [ ] **Save & Cloud Toast**:
  - Click **Publish Post**.
  - Verify redirect to the post detail page.
  - Verify **one single toast** appears in the bottom right corner with real latency metrics (e.g. `Post published — DB 12 ms, S3 118 ms`).
  - Verify toast auto-dismisses after 4 seconds with no bouncing or repeating.

### Checklist 4: Post Detail & Feed Navigation State (bfcache)
- [ ] **Sticky Two-Column Reading**: On desktop, verify image is anchored on the left and title, tags, body, and comments are on the right.
- [ ] **Lightbox**: Click post cover image. Verify it opens in a zero-dependency modal.
- [ ] **Comments & Likes**: Add a comment; verify it appears at the top of comments. Click Like; verify count increments and button toggles to active.
- [ ] **Back Navigation Restoration**:
  - From the home feed, scroll down so at least 2 batches (32 posts) are loaded.
  - Click into any post.
  - Click **Back to all posts** (or browser Back button).
  - Verify the feed returns immediately with all loaded batches intact and scroll position preserved near the clicked post.

### Checklist 5: Trending Analytics & View De-Duplication
- [ ] **View Tracking**: Open a post in a normal browser window. Check `/analytics/` or `/trending/`.
- [ ] **De-duplication**: Refresh the same post 5 times within 5 minutes. Verify only 1 view is recorded.
- [ ] **Trending Page**: Open `/trending/`. Verify:
  - Top 3 posts feature prominently in hero cards with fire badges.
  - Posts 4–10 list in ranked order with score breakdowns.
  - The Hacker News gravity formula is explained clearly at the top.

### Checklist 6: Cloud Activity & System Telemetry
- [ ] **Cloud Activity Page**: Navigate to `/cloud-activity/`.
- [ ] **Live Telemetry Stream**: Verify recent CRUD, view, and AI operations appear with exact millisecond timings for Django, Database, and S3.
- [ ] **System Status Strip**: Toggle the top status bar in Settings; verify it shows `Health: 200 OK`, current region, and active DB engine.

### Checklist 7: Themes & Mobile Polish
- [ ] **Dark Mode Toggle**: In Settings, switch to Dark Mode. Verify page theme changes instantly.
- [ ] **Zero-Flash Reload**: Refresh the page with Dark Mode active. Verify the initial render is dark with zero white flashes.
- [ ] **Mobile Bottom Navigation**: In mobile viewport ($\le 576\text{px}$), verify bottom navigation bar is visible. Tap **More**; verify offcanvas sheet opens with links to Architecture, AI Insights, and Settings.
