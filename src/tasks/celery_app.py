"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

celery_app = Celery(
    "marketview",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks.report_tasks", "src.tasks.data_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Scheduled tasks (beat)
celery_app.conf.beat_schedule = {
    # Generate daily report at 6 AM UTC (before US market open)
    "daily-alpha-brief": {
        "task": "src.tasks.report_tasks.schedule_daily_report",
        "schedule": crontab(hour=6, minute=0),
        "args": (2,),  # Standard level
    },
    # Refresh market data cache every 15 minutes during market hours
    "refresh-market-data": {
        "task": "src.tasks.data_tasks.refresh_market_data",
        "schedule": crontab(minute="*/15", hour="13-21"),  # 8 AM - 4 PM EST
    },
    # Clear old cache entries daily
    "clear-old-cache": {
        "task": "src.tasks.data_tasks.clear_old_cache",
        "schedule": crontab(hour=0, minute=0),
    },
}
