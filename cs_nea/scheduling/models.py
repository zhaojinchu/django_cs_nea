from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from users.models import Student, Teacher

# Lesson request model, used to request a lesson with a teacher
class LessonRequest(models.Model):
    request_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    requested_datetime = models.DateTimeField()
    is_approved = models.BooleanField(default=False)
    is_rescheduling = models.BooleanField(default=False)
    original_lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True)
    request_reason = models.CharField(max_length=255)   
    end_datetime = models.DateTimeField(default=1)
    recurring_amount = models.IntegerField(default=False)
    
    # Additional fields from iteration 2
    is_sent_by_teacher = models.BooleanField(default=False)

    def clean(self):
        if self.requested_datetime <= timezone.now():
            raise ValidationError("Requested datetime must be in the future.")
        if not self.request_reason.strip():
            raise ValidationError("Request reason cannot be empty or just whitespace.")
        if self.end_datetime <= self.requested_datetime:
            raise ValidationError("End datetime must be after the requested datetime.")
        if self.recurring_amount < 1 or self.recurring_amount > 52:
            raise ValidationError("Recurring amount must be between 1 and 52.")

# Lesson model, used store scheduled lessons
class Lesson(models.Model):
    lesson_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    request = models.ForeignKey(LessonRequest, on_delete=models.SET_NULL, null=True)
    start_datetime = models.DateTimeField()
    student_attendance = models.BooleanField(default=False)
    end_datetime = models.DateTimeField()

    def clean(self):
        if self.start_datetime <= timezone.now():
            raise ValidationError("Start datetime must be in the future.")
        if self.end_datetime <= self.start_datetime:
            raise ValidationError("End datetime must be after the start datetime.")

# Other event model, used to schedule events that are not lessons
class OtherEvent(models.Model):
    event_id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    event_description = models.CharField(max_length=255)
    recurring_amount = models.IntegerField()

    def clean(self):
        if self.start_datetime <= timezone.now():
            raise ValidationError("Start datetime must be in the future.")
        if self.end_datetime <= self.start_datetime:
            raise ValidationError("End datetime must be after the start datetime.")
        if not self.event_description.strip():
            raise ValidationError("Event description cannot be empty or just whitespace.")
        if self.recurring_amount < 1 or self.recurring_amount > 52:
            raise ValidationError("Recurring amount must be between 1 and 52.")