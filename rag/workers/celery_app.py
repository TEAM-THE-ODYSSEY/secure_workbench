"""
Celery application instance for worker processes.
Re-exports the Celery app from the workers package.
"""

from rag.workers import app

celery_app = app

__all__ = ["app", "celery_app"]
