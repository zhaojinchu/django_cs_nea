from celery.schedules import crontab

# Celery task manager configuration
CELERY_BEAT_SCHEDULE = {
    "check-scheduled-notifications-every-5-minutes": {
        "task": "communications.tasks.check_scheduled_notifications",
        "schedule": crontab(minute="*/5"), # Runs checks every 5 minutes
    },
}
