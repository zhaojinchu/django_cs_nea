from django.db import models
from django.contrib.auth import get_user_model

# Linking to user models in other app
User = get_user_model()


# Notification config and settings model
class NotificationConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    receive_notification = models.BooleanField(default=True)
    lesson_reminder = models.BooleanField(default=True)
    assignment_notification = models.BooleanField(default=True)
    message_notification = models.BooleanField(default=True)
    attendance_notification = models.BooleanField(default=True)
    t2r_requests = models.BooleanField(default=True)
    cancellation_notification = models.BooleanField(default=True)


# Notification model
class Notification(models.Model):
    receiver = models.ForeignKey(
        User, related_name="received_notifications", on_delete=models.CASCADE
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Notification for {self.receiver.username}: {self.content[:50]}..."


# Message model
class Message(models.Model):
    sender = models.ForeignKey(
        User, related_name="sent_messages", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User, related_name="received_messages", on_delete=models.CASCADE
    )
    message_content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)


# Message config and settings model
class MessageConfig(models.Model):
    student = models.ForeignKey(
        User, related_name="student_message_config", on_delete=models.CASCADE
    )
    teacher = models.ForeignKey(
        User, related_name="teacher_message_config", on_delete=models.CASCADE
    )
    read_only = models.BooleanField(default=False)
