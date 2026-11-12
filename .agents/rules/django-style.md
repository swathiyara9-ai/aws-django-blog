# Django and Python style rules

- Follow PEP 8. Add a docstring to every function, class and view explaining its purpose.
- Use Django class-based views where they reduce code (ListView, DetailView, CreateView, UpdateView, DeleteView); use function views for small custom endpoints (AJAX, tracking).
- Protect author-only actions with `LoginRequiredMixin` and `UserPassesTestMixin` (or equivalent).
- Keep business logic out of views: put it in `services.py` (e.g. `ai_assist/services.py`, `analytics/services.py`).
- Always create and run migrations after model changes; never edit applied migrations.
- Use Django forms for validation. Never trust raw request data.
- Settings: read secrets and environment-specific values from environment variables (`os.environ`), with safe local defaults only for non-secret values.
- Templates: one `base.html`, extend it. Use Bootstrap via CDN. Keep templates simple and readable.
- Write at least basic tests for models and permissions (`python manage.py test`).
- Comments should explain why, not restate what.
