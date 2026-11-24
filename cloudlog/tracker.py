import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from django.conf import settings
from .models import ActivityEvent


def get_db_service_label() -> str:
    """Return 'SQLite (local)' when running SQLite, or 'RDS PostgreSQL' otherwise."""
    engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'sqlite' in engine.lower():
        return 'SQLite (local)'
    return 'RDS PostgreSQL'


class CloudTracker:
    """
    Context manager and helper that times real cloud operations using time.perf_counter.
    Produces truthful breakdown logs (steps) and saves ActivityEvent records.
    """
    def __init__(self, action: str, user=None, post_id: Optional[int] = None, post_title: str = ""):
        self.action = action
        self.user = user if (user and getattr(user, 'is_authenticated', False)) else None
        self.post_id = post_id
        self.post_title = post_title or ""
        self.steps: List[Dict[str, Any]] = []
        self._start_time = time.perf_counter()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Auto-save when exiting context block
        self.save()
        return False  # Do not suppress any inner exceptions

    @contextmanager
    def step(self, service: str, label: str, detail: str = ""):
        """Measure the real elapsed time of a single sub-step."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.steps.append({
                "service": service,
                "label": label,
                "ms": elapsed_ms,
                "detail": str(detail)
            })

    def record_step(self, service: str, label: str, ms: float, detail: str = ""):
        """Manually append a pre-timed step."""
        self.steps.append({
            "service": service,
            "label": label,
            "ms": round(ms, 2),
            "detail": str(detail)
        })

    def save(self) -> Optional[ActivityEvent]:
        """Commit ActivityEvent to database. Silently logs if DB error so core app is never broken."""
        total_ms = round((time.perf_counter() - self._start_time) * 1000.0, 2)
        try:
            event = ActivityEvent.objects.create(
                user=self.user,
                action=self.action,
                post_id=self.post_id,
                post_title=self.post_title[:255] if self.post_title else "",
                steps=self.steps,
                total_ms=total_ms,
            )
            return event
        except Exception:
            return None
