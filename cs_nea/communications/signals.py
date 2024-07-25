from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import NotificationConfig

User = get_user_model()

# Creates a notification config when a user is created
@receiver(post_save, sender=User)
def create_notification_config(sender, instance, created, **kwargs):
    if created:
        NotificationConfig.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_notification_config(sender, instance, **kwargs):
    instance.notificationconfig.save()