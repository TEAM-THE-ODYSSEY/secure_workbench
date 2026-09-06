"""
Celery application configuration for asynchronous ingestion processing.
"""

from celery import Celery

from rag.config import config

app = Celery(
    "mrpl_knowledge_worker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=["rag.workers.ingestion_worker"],
)

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Explicit Task Imports
    imports=["rag.workers.ingestion_worker"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "rag.workers.ingestion_worker.process_ingestion_job": {"queue": "ingestion"},
    },

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,

    # Result expiry (24 hours)
    result_expires=86400,

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Auto-discover tasks
app.autodiscover_tasks(["rag.workers"])

celery_app = app
__all__ = ["app", "celery_app"]
