"""Celery application for background jobs (sitemap feed generation).

Broker/result backend default to Redis. Tasks live in modules listed in
``include`` and are imported when the worker starts:

    celery -A app.celery_app worker --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "chatbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
    include=["app.service.sitemap"],
)

celery_app.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
    broker_connection_retry_on_startup=True,
)
