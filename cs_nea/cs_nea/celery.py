from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# More Celery configuration
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cs_nea.settings")

app = Celery("cs_nea")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Development debug to console
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
