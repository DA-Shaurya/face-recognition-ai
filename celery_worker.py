"""
celery_worker.py — entrypoint for the Celery worker process.
Imports Flask app to trigger ContextTask registration (app context for DB access).
Gets the Celery instance from celery_app to avoid circular imports.
"""
from app import app  # noqa: F401 — triggers ContextTask setup on the celery instance
from celery_app import celery  # noqa: F401 — used by the CLI: celery -A celery_worker.celery worker

if __name__ == "__main__":
    celery.worker_main(["worker", "--loglevel=info", "--concurrency=2"])
