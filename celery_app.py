"""
Standalone Celery factory module.
Imported by app.py (for ContextTask wiring) and celery_worker.py.
Does NOT import Flask to avoid circular imports.
"""
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery("face_recognition", broker=REDIS_URL, backend=REDIS_URL)

celery.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    broker_connection_retry_on_startup=True,
    # Celery Beat — scheduled tasks
    beat_schedule={
        "cleanup-old-uploads": {
            "task": "tasks.cleanup_old_uploads",
            "schedule": 3600.0,  # every hour
        },
    },
)
