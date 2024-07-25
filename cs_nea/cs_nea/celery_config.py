from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "check-scheduled-notifications-every-5-minutes": {
        "task": "communications.tasks.check_scheduled_notifications",
        "schedule": crontab(minute="*/5"),
    },
}
