from django.db import models
from django.contrib.auth import get_user_model
from users.models import Student, Teacher, User

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

    # Lesson reminder notification frequency - iteration 2
    weekly_summary = models.BooleanField(default=False)
    lesson_reminder_1hr = models.BooleanField(default=True)
    lesson_reminder_24hr = models.BooleanField(default=False)
    lesson_reminder_30min = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification Config for {self.user.username}"

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


# Models for messages
class Message(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)

# Models for message configurations
class MessageConfig(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="student_message_configs"
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="teacher_message_configs"
    )
    read_only = models.BooleanField(default=False)
    student = models.ForeignKey(
        User, related_name="student_message_config", on_delete=models.CASCADE
    )
    teacher = models.ForeignKey(
        User, related_name="teacher_message_config", on_delete=models.CASCADE
    )
    read_only = models.BooleanField(default=False)


# Models for assignments
class Assignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    task_content = models.TextField()
    due_date = models.DateTimeField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Task for {self.student} by {self.teacher}"

# Model for student notes
class Note(models.Model):
    note_id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    note_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.student} by {self.teacher}"
