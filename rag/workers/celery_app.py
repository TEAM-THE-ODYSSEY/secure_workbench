"""
Celery application instance for worker processes.
Re-exports the Celery app from the workers package.
"""

from rag.workers import app

__all__ = ["app"]
