from django.utils import timezone
from .models import Notification, NotificationConfig
from scheduling.models import Lesson
from datetime import timedelta
from celery import shared_task

def send_notification(user, content):
    Notification.objects.create(receiver=user, content=content)
    # TODO: Implement other options of sending notifications

def schedule_notifications():
    now = timezone.now()
    for lesson in Lesson.objects.filter(start_datetime__gt=now):
        student_preferences = NotificationConfig.objects.get(user=lesson.student.user)
        teacher_preferences = NotificationConfig.objects.get(user=lesson.teacher.user)

        # Student notifications
        if student_preferences.lesson_reminder_24hr and not lesson.is_student_notification_sent:
            if lesson.start_datetime - now <= timedelta(hours=24):
                send_notification(lesson.student.user, f"Reminder: Your lesson with {lesson.teacher.user.get_full_name()} is in 24 hours.")
                lesson.is_student_notification_sent = True
                lesson.save()

        if student_preferences.lesson_reminder_1hr and not lesson.is_student_notification_sent:
            if lesson.start_datetime - now <= timedelta(minutes=60):
                send_notification(lesson.student.user, f"Reminder: Your lesson with {lesson.teacher.user.get_full_name()} is in 1 hour.")
                lesson.is_student_notification_sent = True
                lesson.save()
                
        if student_preferences.lesson_reminder_30min and not lesson.is_student_notification_sent:
            if lesson.start_datetime - now <= timedelta(minutes=30):
                send_notification(lesson.student.user, f"Reminder: Your lesson with {lesson.teacher.user.get_full_name()} is in 30 minutes.")
                lesson.is_student_notification_sent = True
                lesson.save()

        # Teacher notifications
        if teacher_preferences.lesson_reminder_24hr and not lesson.is_teacher_notification_sent:
            if lesson.start_datetime - now <= timedelta(hours=24):
                send_notification(lesson.teacher.user, f"Reminder: Your lesson with {lesson.student.user.get_full_name()} is in 24 hours.")
                lesson.is_teacher_notification_sent = True
                lesson.save()
                
        if teacher_preferences.lesson_reminder_1hr and not lesson.is_teacher_notification_sent:
            if lesson.start_datetime - now <= timedelta(minutes=30):
                send_notification(lesson.teacher.user, f"Reminder: Your lesson with {lesson.student.user.get_full_name()} is in 1 hour.")
                lesson.is_teacher_notification_sent = True
                lesson.save()
                
        if teacher_preferences.lesson_reminder_30min and not lesson.is_teacher_notification_sent:
            if lesson.start_datetime - now <= timedelta(minutes=30):
                send_notification(lesson.teacher.user, f"Reminder: Your lesson with {lesson.student.user.get_full_name()} is in 30 minutes.")
                lesson.is_teacher_notification_sent = True
                lesson.save()


# Celery definition of task - Celery persistently checks at regular intervals
@shared_task
def check_scheduled_notifications():
    schedule_notifications()