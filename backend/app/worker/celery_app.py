from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "dasmo_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Checks every 15 minutes if auto-pilot is enabled and generates today's quota
        "auto-pilot-check-routine": {
            "task": "app.worker.tasks.auto_pilot_daily_shorts",
            "schedule": 900.0,
        },
    },
)
