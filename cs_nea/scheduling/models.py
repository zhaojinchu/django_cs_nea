from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from users.models import Student, Teacher, User
from django.db import transaction
from communications.models import Notification

# Lesson request model, used to request a lesson with a teacher
class LessonRequest(models.Model):
    request_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    requested_datetime = models.DateTimeField()
    is_approved = models.BooleanField(default=False)
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

    # Additional fields - iteration 2
    is_rescheduled = models.BooleanField(default=False)
    rescheduled_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='rescheduled_from')
    
    # Notification checks - iteration 3
    is_teacher_notification_sent = models.BooleanField(default=False)
    is_student_notification_sent = models.BooleanField(default=False)
    
    def clean(self):
        if self.start_datetime <= timezone.now():
            raise ValidationError("Start datetime must be in the future.")
        if self.end_datetime <= self.start_datetime:
            raise ValidationError("End datetime must be after the start datetime.")
        
    def __str__(self):
        return f"{self.start_datetime.strftime('%Y-%m-%d %H:%M')} - {self.teacher.user.get_full_name()}"
        
    
# Other event model, used to schedule events that are not lessons
class CalendarEvent(models.Model):
    EVENT_TYPES = (
        ('personal', 'Personal'),
        ('work', 'Work'),
        ('other', 'Other'),
    )

    event_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()           
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    all_day = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.title} - {self.teacher.user.get_full_name()}"

    class Meta:
        ordering = ['start_datetime']
        

# Rescheduling request model, used to request a rescheduling of a lesson
class ReschedulingRequest(models.Model):
    rescheduling_id = models.AutoField(primary_key=True)
    original_lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='rescheduling_requests')
    requested_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    requested_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    request_reason = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if self.requested_datetime <= timezone.now():
            raise ValidationError("Requested datetime must be in the future.")
        if self.end_datetime <= self.requested_datetime:
            raise ValidationError("End datetime must be after the requested datetime.")

    def __str__(self):
        return f"Rescheduling request for lesson {self.original_lesson.lesson_id} on {self.requested_datetime}"
    
    # Instead of this in the views.py file, we implement in the model to save space.
    # @transaction.atomic
    # def approve(self):
    #     original_lesson = self.original_lesson
        
    #     # Create new lesson
    #     new_lesson = Lesson.objects.create(
    #         student=original_lesson.student,
    #         teacher=original_lesson.teacher,
    #         start_datetime=self.requested_datetime,
    #         end_datetime=self.end_datetime,
    #         student_attendance=False  # Reset attendance for new lesson
    #     )
        
    #     # Update original lesson
    #     original_lesson.is_rescheduled = True
    #     original_lesson.rescheduled_to = new_lesson
    #     original_lesson.save()
        
    #     # Update rescheduling request
    #     self.is_approved = True
    #     self.save()
        
    #     # Create notifications
    #     Notification.objects.create(
    #         receiver=original_lesson.student.user,
    #         content=f"Lesson on {original_lesson.start_datetime} has been rescheduled to {new_lesson.start_datetime}"
    #     )
    #     Notification.objects.create(
    #         receiver=original_lesson.teacher.user,
    #         content=f"Lesson on {original_lesson.start_datetime} has been rescheduled to {new_lesson.start_datetime}"
    #     )
        
    #     return new_lesson