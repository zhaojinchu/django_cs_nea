
# --- File: .gitignore ---

```plaintext
env/
cs_nea/node_modules/
```

# --- File: .prettierrc ---

```plaintext
{
  "tabWidth": 4,
  "useTabs": false
}

```

# === Directory: cs_nea ===


# --- File: cs_nea/celerybeat-schedule.dir ---

```plaintext
'entries', (0, 379)
'__version__', (512, 20)
'tz', (1024, 18)
'utc_enabled', (1536, 4)

```

# --- File: cs_nea/celerybeat-schedule.dat ---

```plaintext
[Could not decode file: /Users/zhaojin/Documents/django_cs_nea/cs_nea/celerybeat-schedule.dat]

```

# --- File: cs_nea/manage.py ---

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cs_nea.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

```

# --- File: cs_nea/celerybeat-schedule.bak ---

```plaintext
'entries', (0, 379)
'__version__', (512, 20)
'tz', (1024, 18)
'utc_enabled', (1536, 4)

```

# === Directory: cs_nea/scheduling ===


# --- File: cs_nea/scheduling/models.py ---

```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from users.models import Student, Teacher
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
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
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
        return f"Rescheduling request for lesson {self.original_lesson.id} on {self.requested_datetime}"
    
    # Instead of this in the views.py file, we implement in the model to save space.
    @transaction.atomic
    def approve(self):
        original_lesson = self.original_lesson
        
        # Create new lesson
        new_lesson = Lesson.objects.create(
            student=original_lesson.student,
            teacher=original_lesson.teacher,
            start_datetime=self.requested_datetime,
            end_datetime=self.end_datetime,
            student_attendance=False  # Reset attendance for new lesson
        )
        
        # Update original lesson
        original_lesson.is_rescheduled = True
        original_lesson.rescheduled_to = new_lesson
        original_lesson.save()
        
        # Update rescheduling request
        self.is_approved = True
        self.save()
        
        # Create notifications
        Notification.objects.create(
            receiver=original_lesson.student.user,
            content=f"Lesson on {original_lesson.start_datetime} has been rescheduled to {new_lesson.start_datetime}"
        )
        Notification.objects.create(
            receiver=original_lesson.teacher.user,
            content=f"Lesson on {original_lesson.start_datetime} has been rescheduled to {new_lesson.start_datetime}"
        )
        
        return new_lesson
```

# --- File: cs_nea/scheduling/calendar_views.py ---

```python
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from .models import Lesson, CalendarEvent
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from datetime import datetime, timedelta

# Returns calendar view
@login_required
def calendar_view(request):
    return render(request, "scheduling/calendar.html")


# Gets calendar data for AJAX requests
@login_required
@require_GET
def get_calendar_data(request):
    start = timezone.datetime.fromisoformat(request.GET.get("start").replace("Z", "+00:00"))
    end = timezone.datetime.fromisoformat(request.GET.get("end").replace("Z", "+00:00"))

    user_timezone = timezone.get_current_timezone()

    events = []

    if request.user.user_type == 2:  # Teacher
        lessons = Lesson.objects.filter(
            teacher=request.user.teacher,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
        calendar_events = CalendarEvent.objects.filter(
            teacher=request.user.teacher,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
    elif request.user.user_type == 1:  # Student
        lessons = Lesson.objects.filter(
            student=request.user.student,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
        calendar_events = []  # Students don't see calendar events
    else:
        lessons = []
        calendar_events = []

    for lesson in lessons:
        event_title = (
            f"Lesson with {lesson.student.user.get_full_name()}"
            if request.user.user_type == 2
            else f"Lesson with {lesson.teacher.user.get_full_name()}"
        )
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": event_title,
            "start": lesson.start_datetime.astimezone(user_timezone).isoformat(),
            "end": lesson.end_datetime.astimezone(user_timezone).isoformat(),
            "color": "blue",
            "editable": False,
        })

    for event in calendar_events:
        events.append({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.astimezone(user_timezone).isoformat(),
            "end": event.end_datetime.astimezone(user_timezone).isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })

    return JsonResponse(events, safe=False)


# Calendar views for AJAX requests to create, update, and delete events
@login_required
@require_POST
def create_event(request):
    title = request.POST.get("title")
    start_str = request.POST.get("start")
    end_str = request.POST.get("end")
    all_day = request.POST.get("allDay") == "true"
    event_type = request.POST.get("event_type", "other")
    timezone_offset = int(request.POST.get('timezone_offset', 0))
    
    try:
        if all_day:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(datetime.combine(start, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(end, datetime.max.time()))
        else:
            start_datetime = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
            
            # Convert to UTC
            start_datetime = timezone.make_aware(start_datetime) + timedelta(minutes=timezone_offset)
            end_datetime = timezone.make_aware(end_datetime) + timedelta(minutes=timezone_offset)

        event = CalendarEvent.objects.create(
            teacher=request.user.teacher,
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            all_day=all_day,
        )

        return JsonResponse({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

# Updates an event in case of changes
@login_required
@require_POST
def update_event(request):
    event_id = request.POST.get("id")
    if not event_id.startswith("event_"):
        return JsonResponse({"error": "Can only update calendar events"}, status=400)

    event = get_object_or_404(CalendarEvent, event_id=event_id[6:])
    if event.teacher != request.user.teacher:
        return JsonResponse({"error": "Permission denied"}, status=403)

    title = request.POST.get("title")
    start_str = request.POST.get("start")
    end_str = request.POST.get("end")
    all_day = request.POST.get("allDay") == "true"
    timezone_offset = int(request.POST.get("timezone_offset", 0))

    try:
        if all_day:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            event.start_datetime = timezone.make_aware(datetime.combine(start, datetime.min.time()))
            event.end_datetime = timezone.make_aware(datetime.combine(end, datetime.max.time()))
        else:
            start_datetime = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
            
            # Applies timezone offset
            start_datetime = start_datetime + timedelta(minutes=timezone_offset)
            end_datetime = end_datetime + timedelta(minutes=timezone_offset)
            
            event.start_datetime = timezone.make_aware(start_datetime)
            event.end_datetime = timezone.make_aware(end_datetime)

        event.title = title
        event.all_day = all_day
        event.save()

        return JsonResponse({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)


# Deletes an event
@login_required
@require_POST
def delete_event(request):
    event_id = request.POST.get("id")
    if not event_id.startswith("event_"):
        return JsonResponse({"error": "Can only delete calendar events"}, status=400)

    event = get_object_or_404(CalendarEvent, event_id=event_id[6:])
    if event.teacher != request.user.teacher:
        return JsonResponse({"error": "Permission denied"}, status=403)

    event.delete()
    return JsonResponse({"success": True})

```

# --- File: cs_nea/scheduling/__init__.py ---

```python

```

# --- File: cs_nea/scheduling/apps.py ---

```python
from django.apps import AppConfig

# Scheduling app config
class SchedulingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduling'

```

# --- File: cs_nea/scheduling/forms.py ---

```python
from django import forms
from .models import LessonRequest, Lesson, ReschedulingRequest
from users.models import Teacher, Student, Invite
from django.utils import timezone
from pytz import timezone as pytz_timezone
import pytz


# Lesson request form for students
class StudentLessonRequestForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.none(),
        empty_label="Select a teacher",
        widget=forms.Select(attrs={"class": "form-control", "id": "teacher-select"}),
    )

    class Meta:
        model = LessonRequest
        fields = [
            "teacher",
            "requested_datetime",
            "end_datetime",
            "request_reason",
            "recurring_amount",
        ]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "recurring_amount": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        user_timezone = self.data.get("timezone")

        if user_timezone:
            user_timezone = pytz_timezone(user_timezone)

            if requested_datetime:
                if requested_datetime.tzinfo is not None:
                    requested_datetime = requested_datetime.replace(tzinfo=None)
                requested_datetime = user_timezone.localize(requested_datetime)
                cleaned_data["requested_datetime"] = requested_datetime.astimezone(
                    pytz.UTC
                )

            if end_datetime:
                if end_datetime.tzinfo is not None:
                    end_datetime = end_datetime.replace(tzinfo=None)
                end_datetime = user_timezone.localize(end_datetime)
                cleaned_data["end_datetime"] = end_datetime.astimezone(pytz.UTC)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop("student", None)
        super(StudentLessonRequestForm, self).__init__(*args, **kwargs)

        if self.student:
            # Get teachers who are connected to the student
            connected_teachers = Teacher.objects.filter(
                sent_invites__student=self.student, 
                sent_invites__status="accepted"
            ).distinct()

            self.fields["teacher"].queryset = connected_teachers
            self.fields["teacher"].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.user.email})"

# Lesson request form for teachers
class TeacherLessonRequestForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        empty_label="Select a student",
        widget=forms.Select(attrs={"class": "form-control", "id": "id_student"}),
    )
    send_request = forms.BooleanField(required=True, initial=True)

    class Meta:
        model = LessonRequest
        fields = [
            "student",
            "requested_datetime",
            "end_datetime",
            "request_reason",
            "recurring_amount",
        ]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "recurring_amount": forms.NumberInput(attrs={"class": "form-control"}),
        }
        
    # Validates the form
    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        user_timezone = self.data.get("timezone")

        if user_timezone:
            user_timezone = pytz_timezone(user_timezone)

            if requested_datetime:
                if requested_datetime.tzinfo is not None:
                    requested_datetime = requested_datetime.replace(tzinfo=None)
                requested_datetime = user_timezone.localize(requested_datetime)
                cleaned_data["requested_datetime"] = requested_datetime.astimezone(
                    pytz.UTC
                )

            if end_datetime:
                if end_datetime.tzinfo is not None:
                    end_datetime = end_datetime.replace(tzinfo=None)
                end_datetime = user_timezone.localize(end_datetime)
                cleaned_data["end_datetime"] = end_datetime.astimezone(pytz.UTC)

        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop("teacher", None)
        super(TeacherLessonRequestForm, self).__init__(*args, **kwargs)

        if self.teacher:
            # Get students who are connected to the teacher         
            connected_students = Student.objects.filter(
                invites__teacher=self.teacher, 
                invites__status="accepted"
            ).distinct()

            self.fields["student"].queryset = connected_students
            self.fields["student"].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.user.email})"


# Corresponding Django form for the Lesson model
class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "student",
            "teacher",
            "start_datetime",
            "end_datetime",
            "student_attendance",
        ]
        # Custom timedate widgets for the form
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "data-tz": timezone.get_current_timezone_name(),
                }
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "data-tz": timezone.get_current_timezone_name(),
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError("Start datetime must be in the future.")
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise forms.ValidationError(
                "End datetime must be after the start datetime."
            )

        return cleaned_data


# Reschedule lesson form
class RescheduleLessonForm(forms.ModelForm):
    lesson = forms.ModelChoiceField(
        queryset=None,
        label="Select Lesson to Reschedule",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = ReschedulingRequest
        fields = ["lesson", "requested_datetime", "end_datetime", "request_reason"]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(RescheduleLessonForm, self).__init__(*args, **kwargs)
        if self.user:
            if self.user.user_type == 1:
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    student=self.user.student, is_rescheduled=False
                ).order_by("start_datetime")
            else:
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    teacher=self.user.teacher, is_rescheduled=False
                ).order_by("start_datetime")

    # Validates the form
    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if requested_datetime and requested_datetime <= timezone.now():
            raise forms.ValidationError("Requested datetime must be in the future.")

        if end_datetime and requested_datetime and end_datetime <= requested_datetime:
            raise forms.ValidationError(
                "End datetime must be after the requested datetime."
            )

        return cleaned_data

```

# --- File: cs_nea/scheduling/admin.py ---

```python
from django.contrib import admin

# Register your models here.

```

# --- File: cs_nea/scheduling/tests.py ---

```python
from django.test import TestCase

# Create your tests here.

```

# --- File: cs_nea/scheduling/urls.py ---

```python
from django.urls import path
from . import views
from .calendar_views import (
    calendar_view,
    get_calendar_data,
    create_event,
    update_event,
    delete_event,
)

urlpatterns = [
    #path("create_lesson", views.create_lesson, name="create_lesson"),

    # Path for creating student and teacher lesson requests
    path(
        "student/request_lesson/",
        views.student_lesson_request,
        name="student_lesson_request",
    ),
    path(
        "teacher/request_lesson/",
        views.teacher_lesson_request,
        name="teacher_lesson_request",
    ),
    # Path for accepting and listing lesson requests
    path("lesson_requests/", views.lesson_requests, name="lesson_requests"),
    path(
        "accept_lesson_request/<int:request_id>/",
        views.accept_lesson_request,
        name="accept_lesson_request",
    ),
    # Path for declining lesson requests
    path(
        "decline_lesson_request/<int:request_id>/",
        views.decline_lesson_request,
        name="decline_lesson_request",
    ),
    # Path for rescheduling lesson requests
    path("reschedule_lesson/", views.reschedule_lesson, name="reschedule_lesson"),
    path(
        "accept_rescheduling_request/<int:rescheduling_request_id>/",
        views.accept_rescheduling_request,
        name="accept_rescheduling_request",
    ),
    path(
        "decline_rescheduling_request/<int:rescheduling_request_id>/",
        views.decline_rescheduling_request,
        name="decline_rescheduling_request",
    ),
    # Calendar URLs
    path("calendar/", calendar_view, name="calendar"),
    path("get_calendar_data/", get_calendar_data, name="get_calendar_data"),
    # Calendar AJAX URLs
    path("create_event/", create_event, name="create_event"),
    path("update_event/", update_event, name="update_event"),
    path("delete_event/", delete_event, name="delete_event"),
    
    # Fetching teacher schedule URL
    path('get_teacher_schedule/<int:teacher_id>/', views.get_teacher_schedule, name='get_teacher_schedule'),
    # Fetching student schedule URL
    path('get_student_schedule/<int:student_id>/', views.get_student_schedule, name='get_student_schedule'),
    
    # Attendance related URLs
    path('get_recent_lessons/', views.get_recent_lessons, name='get_recent_lessons'),
    path('update_attendance/', views.update_attendance, name='update_attendance'),
]

```

# --- File: cs_nea/scheduling/views.py ---

```python
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .forms import (
    StudentLessonRequestForm,
    TeacherLessonRequestForm,
    LessonForm,
    RescheduleLessonForm,
)
from .models import (
    Student,
    Teacher,
    Lesson,
    LessonRequest,
    ReschedulingRequest,
    CalendarEvent
)
from communications.models import Notification
from datetime import timedelta
from django.db import transaction
from communications.models import Notification, NotificationConfig
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Predefined functions for checking user type
def is_teacher(user):
    return user.user_type == 2


def is_student(user):
    return user.user_type == 1


# Student lesson request form
@login_required
@user_passes_test(is_student)
def student_lesson_request(request):
    if request.method == "POST":
        form = StudentLessonRequestForm(request.POST, student=request.user.student)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.student = request.user.student
            lesson_request.is_rescheduling = False

            lesson_request.requested_datetime = form.cleaned_data['requested_datetime']
            lesson_request.end_datetime = form.cleaned_data['end_datetime']

            lesson_request.save()
            teacher = lesson_request.teacher
            
            notification_config, created = NotificationConfig.objects.get_or_create(
                    user=teacher.user
            )
            
            if notification_config.receive_notification:
                # Create and send notification
                notification = Notification.objects.create(
                    receiver=lesson_request.teacher.user,
                    content=f"New lesson request from {request.user.get_full_name()}",
                    timestamp=timezone.now().isoformat(),
                )

                # Send real-time notification
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{lesson_request.teacher.user.id}_notifications",
                    {
                        "type": "notification",
                        "notification": {
                            "id": notification.id,
                            "content": notification.content,
                            "timestamp": notification.timestamp.isoformat(),
                            "is_read": notification.is_read
                        }
                    }
                )

            messages.success(request, "Lesson request submitted successfully!")
            return redirect("dashboard")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentLessonRequestForm(student=request.user.student)

    return render(request, "scheduling/student_schedule_lesson.html", {"form": form})


# Fetching teacher schedule for scheduling view
@login_required
@user_passes_test(is_student)
def get_teacher_schedule(request, teacher_id):
    teacher = get_object_or_404(Teacher, teacher_id=teacher_id)
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=30)  # Get events for the next 30 days only

    lessons = Lesson.objects.filter(
        teacher=teacher,
        start_datetime__gte=start,
        end_datetime__lte=end,
    )

    calendar_events = CalendarEvent.objects.filter(
        teacher=teacher,
        start_datetime__gte=start,
        end_datetime__lte=end,
    )

    # Creating and posting lesson or events to calendar
    events = []
    for lesson in lessons:
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": "Busy",
            "start": lesson.start_datetime.isoformat(),
            "end": lesson.end_datetime.isoformat(),
            "color": "blue",
        })

    for event in calendar_events:
        events.append({
            "id": f"event_{event.event_id}",
            "title": "Busy",
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "green",
        })

    return JsonResponse(events, safe=False)


# Teacher lesson request form
@login_required
@user_passes_test(is_teacher)
def teacher_lesson_request(request):
    if request.method == "POST":
        form = TeacherLessonRequestForm(request.POST, teacher=request.user.teacher)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.teacher = request.user.teacher
            lesson_request.is_rescheduling = False
            lesson_request.is_sent_by_teacher = True
            
            lesson_request.requested_datetime = form.cleaned_data['requested_datetime']
            lesson_request.end_datetime = form.cleaned_data['end_datetime']

            if form.cleaned_data["send_request"]:
                lesson_request.save()
                student = lesson_request.student

                # Get or create NotificationConfig for the teacher
                notification_config, created = NotificationConfig.objects.get_or_create(
                    user=student.user
                )

                if notification_config.receive_notification:
                    recurring_text = (
                        f" (recurring {lesson_request.recurring_amount} times)"
                        if lesson_request.recurring_amount > 1
                        else ""
                    )
                    notification = Notification.objects.create(
                        receiver=student.user,
                        content=f"New lesson request from {request.user.get_full_name()}{recurring_text}",
                        timestamp=timezone.now().isoformat(),
                    )
                    # Send real-time notification
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"user_{lesson_request.student.user.id}_notifications",
                        {
                            "type": "notification",
                            "notification": {
                                "id": notification.id,
                                "content": notification.content,
                                "timestamp": notification.timestamp.isoformat(),
                                "is_read": notification.is_read
                            }
                        }
                    )
                    
                    messages.success(request, "Lesson request sent to student.")
                    return redirect("dashboard")
                
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")

                
            else:
                # Create multiple lessons based on recurring amount
                lesson_duration = (
                    lesson_request.end_datetime - lesson_request.requested_datetime
                )

                for i in range(lesson_request.recurring_amount):
                    start_time = lesson_request.requested_datetime + timedelta(weeks=i)
                    end_time = start_time + lesson_duration

                    Lesson.objects.create(
                        student=lesson_request.student,
                        teacher=request.user.teacher,
                        start_datetime=start_time,
                        end_datetime=end_time,
                    )

                if lesson_request.student.user.notification_preferences.lessons:
                    recurring_text = (
                        f" (recurring {lesson_request.recurring_amount} times)"
                        if lesson_request.recurring_amount > 1
                        else ""
                    )
                    notification = Notification.objects.create(
                        receiver=lesson_request.student.user,
                        content=f"New lesson{recurring_text} scheduled with {request.user.get_full_name()}",
                    )
                    
                    # Send real-time notification
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"user_{lesson_request.student.user.id}_notifications",
                        {
                            "type": "notification",
                            "notification": {
                                "id": notification.id,
                                "content": notification.content,
                                "timestamp": notification.timestamp.isoformat(),
                                "is_read": notification.is_read
                            }
                        }
                    )
                messages.success(
                    request,
                    f"{lesson_request.recurring_amount} lesson{'s' if lesson_request.recurring_amount > 1 else ''} scheduled successfully.",
                )

            return redirect("dashboard")
    else:
        form = TeacherLessonRequestForm(teacher=request.user.teacher)

    return render(request, "scheduling/teacher_schedule_lesson.html", {"form": form})

# Fetching student schedule for scheduling view
@login_required
@user_passes_test(is_teacher)
def get_student_schedule(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=30)  # Get events for the next 30 days only

    lessons = Lesson.objects.filter(
        student=student,
        start_datetime__gte=start,
        end_datetime__lte=end,
    )

    events = []
    for lesson in lessons:
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": f"Lesson with {Teacher.objects.get(teacher_id=lesson.teacher_id).user.get_full_name()}",
            "start": lesson.start_datetime.isoformat(),
            "end": lesson.end_datetime.isoformat(),
            "color": "blue",
        })

    return JsonResponse(events, safe=False)

# Create lesson view
"""
@login_required
def create_lesson(request):
    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.student = Student.objects.get(user=request.user)
            lesson.start_datetime = timezone.make_aware(form.cleaned_data['start_datetime'])
            lesson.end_datetime = timezone.make_aware(form.cleaned_data['end_datetime'])
            lesson.save()
            messages.success(request, "Lesson created successfully!")
            return redirect("lesson_list")
    else:
        form = LessonForm()

    return render(request, "scheduling/create_lesson.html", {"form": form})
"""

# View for listing lessons requests
@login_required
def lesson_requests(request):
    if request.user.user_type == 1:  # Student
        scheduling_requests = LessonRequest.objects.filter(
            student=request.user.student, is_approved=False, is_sent_by_teacher=True
        )
        rescheduling_requests = ReschedulingRequest.objects.filter(
            original_lesson__student=request.user.student, is_approved=False
        )
    else:  # Teacher
        scheduling_requests = LessonRequest.objects.filter(
            teacher=request.user.teacher, is_approved=False, is_sent_by_teacher=False
        )
        rescheduling_requests = ReschedulingRequest.objects.filter(
            original_lesson__teacher=request.user.teacher, is_approved=False
        )
    
    context = {
        "scheduling_requests": scheduling_requests,
        "rescheduling_requests": rescheduling_requests,
    }
    return render(request, "scheduling/lesson_requests.html", context)


# View for accepting a lesson request
@login_required
def accept_lesson_request(request, request_id):
    lesson_request = get_object_or_404(LessonRequest, pk=request_id)

    if (
        request.user.user_type == 1 and lesson_request.student != request.user.student
    ) or (
        request.user.user_type == 2 and lesson_request.teacher != request.user.teacher
    ):
        messages.error(request, "You don't have permission to accept this request.")
        return redirect("lesson_requests")

    try:
        with transaction.atomic():
            lesson_duration = (
                lesson_request.end_datetime - lesson_request.requested_datetime
            )

            for i in range(lesson_request.recurring_amount):
                start_time = lesson_request.requested_datetime + timedelta(weeks=i)
                end_time = start_time + lesson_duration

                Lesson.objects.create(
                    student=lesson_request.student,
                    teacher=lesson_request.teacher,
                    start_datetime=start_time,
                    end_datetime=end_time,
                    request=lesson_request,
                )

            lesson_request.is_approved = True
            lesson_request.save()

            # Notifications
            user_notification_pref = NotificationConfig.objects.filter(user=lesson_request.teacher.user).first()
            if user_notification_pref and user_notification_pref.receive_notification:
                    recurring_text = (
                        f" (recurring {lesson_request.recurring_amount} times)"
                        if lesson_request.recurring_amount > 1
                        else ""
                    )
                    notification = Notification.objects.create(
                        receiver=lesson_request.student.user,
                        content=f"New lesson{recurring_text} scheduled with {request.user.get_full_name()}",
                    )
                    
                    # Send real-time notification
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"user_{lesson_request.student.user.id}_notifications",
                        {
                            "type": "notification",
                            "notification": {
                                "id": notification.id,
                                "content": notification.content,
                                "timestamp": notification.timestamp.isoformat(),
                                "is_read": notification.is_read
                            }
                        }
                    )
            messages.success(
                request,
                f"{lesson_request.recurring_amount} lesson{'s' if lesson_request.recurring_amount > 1 else ''} scheduled successfully.",
            )
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("lesson_requests")


# View for declining a lesson request
@login_required
def decline_lesson_request(request, request_id):
    lesson_request = get_object_or_404(LessonRequest, pk=request_id)

    if (
        request.user.user_type == 1 and lesson_request.student != request.user.student
    ) or (
        request.user.user_type == 2 and lesson_request.teacher != request.user.teacher
    ):
        messages.error(request, "You don't have permission to decline this request.")
        return redirect("lesson_requests")

    lesson_request.delete()
    messages.success(request, "Lesson request declined and deleted.")
    return redirect("lesson_requests")


# Reschedule lesson view
@login_required
def reschedule_lesson(request):
    if request.method == "POST":
        form = RescheduleLessonForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    rescheduling_request = form.save(commit=False)
                    rescheduling_request.requested_by = request.user
                    rescheduling_request.original_lesson = form.cleaned_data["lesson"]
                    rescheduling_request.requested_datetime = timezone.make_aware(form.cleaned_data['requested_datetime'])
                    rescheduling_request.end_datetime = timezone.make_aware(form.cleaned_data['end_datetime'])
                    rescheduling_request.save()

                    # Create notification for the other party
                    other_user = (
                        rescheduling_request.original_lesson.teacher.user
                        if request.user.user_type == 1
                        else rescheduling_request.original_lesson.student.user
                    )
                    Notification.objects.create(
                        receiver=other_user,
                        content=f"New rescheduling request for lesson on {rescheduling_request.original_lesson.start_datetime}",
                    )

                messages.success(
                    request, "Rescheduling request submitted successfully!"
                )
                return redirect("dashboard")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RescheduleLessonForm(user=request.user)

    return render(request, "scheduling/reschedule_lesson.html", {"form": form})

# Accepts a rescheduling request
@login_required
def accept_rescheduling_request(request, rescheduling_request_id):
    rescheduling_request = get_object_or_404(
        ReschedulingRequest, rescheduling_id=rescheduling_request_id
    )

    if request.user.user_type == 1:  # Student
        if request.user.student != rescheduling_request.original_lesson.student:
            messages.error(
                request,
                "You don't have permission to accept this rescheduling request.",
            )
            return redirect("lesson_requests")
    elif request.user.user_type == 2:  # Teacher
        if request.user.teacher != rescheduling_request.original_lesson.teacher:
            messages.error(
                request,
                "You don't have permission to accept this rescheduling request.",
            )
            return redirect("lesson_requests")
    else:
        messages.error(request, "Invalid user type.")
        return redirect("lesson_requests")

    try:
        new_lesson = rescheduling_request.approve()
        messages.success(
            request, f"Lesson rescheduled successfully to {new_lesson.start_datetime}."
        )
    except Exception as e:
        messages.error(request, f"An error occurred while rescheduling: {str(e)}")

    return redirect("lesson_requests")

# Declines a rescheduling request
@login_required
def decline_rescheduling_request(request, rescheduling_request_id):
    rescheduling_request = get_object_or_404(
        ReschedulingRequest, rescheduling_id=rescheduling_request_id
    )

    if request.user.user_type == 1:  # Student
        if request.user.student != rescheduling_request.original_lesson.student:
            messages.error(
                request,
                "You don't have permission to decline this rescheduling request.",
            )
            return redirect("lesson_requests")
    elif request.user.user_type == 2:  # Teacher
        if request.user.teacher != rescheduling_request.original_lesson.teacher:
            messages.error(
                request,
                "You don't have permission to decline this rescheduling request.",
            )
            return redirect("lesson_requests")
    else:
        messages.error(request, "Invalid user type.")
        return redirect("lesson_requests")

    rescheduling_request.delete()
    messages.success(request, "Rescheduling request declined and deleted.")
    return redirect("lesson_requests")


# Attendance views
@login_required
@user_passes_test(is_teacher)
def get_recent_lessons(request):
    now = timezone.now()
    recent_lessons = Lesson.objects.filter(
        teacher=request.user.teacher,
        start_datetime__lte=now,
        start_datetime__gte=now - timezone.timedelta(days=7)
    ).order_by('-start_datetime')[:10]  # Get last 10 lessons within past week

    lessons_data = [{
        'lesson_id': lesson.lesson_id,
        'start_time': lesson.start_datetime.strftime('%Y-%m-%d %H:%M'),
        'student_name': lesson.student.user.get_full_name(),
        'attendance': lesson.student_attendance
    } for lesson in recent_lessons]

    return JsonResponse(lessons_data, safe=False)


# Updates attendance for a lesson
@require_POST
@login_required
@user_passes_test(is_teacher)
def update_attendance(request):
    data = json.loads(request.body)
    lesson_id = data.get('lesson_id')
    attended = data.get('attended')

    try:
        lesson = Lesson.objects.get(lesson_id=lesson_id, teacher=request.user.teacher)
        lesson.student_attendance = attended
        lesson.save()
        return JsonResponse({'success': True})
    except Lesson.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lesson not found'}, status=404)

```

# === Directory: cs_nea/cs_nea ===


# --- File: cs_nea/cs_nea/asgi.py ---

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import communications.routing  # you'll create this in step 6

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cs_nea.settings')

# Application definition and websocket routing
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            communications.routing.websocket_urlpatterns
        )
    ),
})
```

# --- File: cs_nea/cs_nea/__init__.py ---

```python

```

# --- File: cs_nea/cs_nea/celery_config.py ---

```python
from celery.schedules import crontab

# Celery task manager configuration
CELERY_BEAT_SCHEDULE = {
    "check-scheduled-notifications-every-5-minutes": {
        "task": "communications.tasks.check_scheduled_notifications",
        "schedule": crontab(minute="*/5"), # Runs checks every 5 minutes
    },
}

```

# --- File: cs_nea/cs_nea/celery.py ---

```python
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

```

# --- File: cs_nea/cs_nea/settings.py ---

```python
"""
Django settings for cs_nea project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-z&kc3iy^14wh+aj5q7@rt7mxnwr&^xj=3#*(g8o-uh8$-a-q=4"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Additional apps for real time messaging - these two must come before staticfiles
    "daphne",
    "channels",
    "django.contrib.staticfiles",
    # Additional apps
    "tailwind",
    "theme",
    "django_browser_reload",
    "widget_tweaks",
    "phonenumber_field",
    # My django apps
    "users",
    "dashboard",
    "scheduling",
    "communications",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    # Automatic page refreshes
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cs_nea.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Path to the templates folder
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cs_nea.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TAILWIND_APP_NAME = "theme"

INTERNAL_IPS = [
    "127.0.0.1",
]

LOGIN_URL = "index"
LOGIN_REDIRECT_URL = "dashboard"

# Email sending details and settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"  
EMAIL_PORT = 587
EMAIL_USE_TLS = True  
EMAIL_HOST_USER = "zhaojin.chu07@gmail.com"  
EMAIL_HOST_PASSWORD = "wxwk ximf qxzy oiyl"  
DEFAULT_FROM_EMAIL = (
    "zhaojin.chu07@gmail.com" 
)

# Settings for real time messaging
ASGI_APPLICATION = "cs_nea.asgi.application"

# Uses the in-memory channel layer
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Timezone settings
USE_TZ = True
TIME_ZONE = "UTC"

# Celery settings
CELERY_BROKER_URL = "redis://localhost:6379/0"  # Using Redis as broker
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"  # Storing results in Redis
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    "check-scheduled-notifications-every-5-minutes": {
        "task": "communications.tasks.check_scheduled_notifications",
        "schedule": crontab(minute="*/5"),
    },
}

```

# --- File: cs_nea/cs_nea/urls.py ---

```python
"""
URL configuration for cs_nea project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

# Importing all the URLs from the apps into main file routing
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("users.urls")),
    path("", include("dashboard.urls")),
    path("", include("scheduling.urls")),
    path("", include("communications.urls")),
    path("__reload__/", include("django_browser_reload.urls")),
    
]

```

# --- File: cs_nea/cs_nea/wsgi.py ---

```python
"""
WSGI config for cs_nea project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cs_nea.settings')

application = get_wsgi_application()

```

# === Directory: cs_nea/dashboard ===


# --- File: cs_nea/dashboard/models.py ---

```python
from django.db import models

# Create your models here.

```

# --- File: cs_nea/dashboard/__init__.py ---

```python

```

# --- File: cs_nea/dashboard/apps.py ---

```python
from django.apps import AppConfig

# Dashboard app config
class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

```

# --- File: cs_nea/dashboard/admin.py ---

```python
from django.contrib import admin
```

# --- File: cs_nea/dashboard/tests.py ---

```python
from django.test import TestCase

# Create your tests here.

```

# --- File: cs_nea/dashboard/urls.py ---

```python
from django.urls import path
from .views import dashboard, student_dashboard, teacher_dashboard   

# URLS to the default dashboard view
urlpatterns = [
    path("dashboard", dashboard, name="dashboard"),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
]

```

# --- File: cs_nea/dashboard/views.py ---

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from communications.models import Notification

# Predefined functions to check user type
def is_student(user):
    return user.user_type == 1


def is_teacher(user):
    return user.user_type == 2


# Dashboard redirect to teacher or student dashboard
@login_required
def dashboard(request):
    notifications = Notification.objects.filter(
        receiver=request.user, is_read=False
    ).order_by("-timestamp")[:20]

    context = {
        "notifications": notifications,
    }

    if request.user.user_type == 1:  # Student
        return render(request, "dashboard/student_dashboard.html", context)
    elif request.user.user_type == 2:  # Teacher
        return render(request, "dashboard/teacher_dashboard.html", context)
    else:
        # Handle unexpected user type
        return redirect("home")


@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    # Student-specific dashboard logic
    return render(request, "dashboard/student_dashboard.html")


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    # Teacher-specific dashboard logic
    return render(request, "dashboard/teacher_dashboard.html")

```

# === Directory: cs_nea/static ===


# === Directory: cs_nea/static/media ===


# === Directory: cs_nea/users ===


# --- File: cs_nea/users/models.py ---

```python
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator, MinLengthValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.utils.crypto import get_random_string

# Base user model containing basic user information
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    # User types
    USER_TYPE_CHOICES = (
        (1, "Student"),
        (2, "Teacher"),
    )
    user_type = models.PositiveSmallIntegerField(
        choices=USER_TYPE_CHOICES,
        default=1,
    )

    email = models.EmailField(
        "email address",
        max_length=255,
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
    )
    first_name = models.CharField(
        "first name",
        max_length=150,
        validators=[
            RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid first name (letters only).")
        ],
    )
    last_name = models.CharField(
        "last name",
        max_length=150,
        validators=[
            RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid last name (letters only).")
        ],
    )
    password = models.CharField(
        "password",
        max_length=255,
        validators=[
            MinLengthValidator(6),
            RegexValidator(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{6,}$",
                "Password must have at least 6 characters, including a number and a capital letter.",
            ),
        ],
    )

    contact_number = PhoneNumberField()

    date_of_birth = models.DateField("date of birth")

    # Two-factor authentication fields
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_code = models.CharField(max_length=6, blank=True, null=True)
    two_factor_code_expiry = models.DateTimeField(blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, null=True, blank=True)
    password_reset_token_created_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["__all__"]

    # Account authentication and retrival methods
    def generate_password_reset_token(self):
        self.password_reset_token = get_random_string(length=32)
        self.password_reset_token_created_at = timezone.now()
        self.save()

    def generate_two_factor_code(self):
        self.two_factor_code = get_random_string(length=6, allowed_chars="0123456789")
        self.two_factor_code_expiry = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        
    # Full name quick access method
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    # First name quick access method
    def get_first_name(self):
        return self.first_name

    # String representation of the user - method is used for all Django models below
    def __str__(self):
        return self.email


# Teacher model
class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    extra_teacher_info = models.TextField(
        "extra / optional teacher information",
        max_length=2000,
        blank=True,  # This field is optional
        null=True,
    )
    
    def __str__(self):
        return f"{self.user.get_first_name()} ({self.user.email})"


# Student model
class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    extra_student_info = models.TextField(
        "extra / optional student information",
        max_length=2000,
        blank=True,  # This field is optional
        null=True,
    )
    grade_level = models.IntegerField(
        "grade level",
        validators=[
            RegexValidator(r"^\d+$", "Enter a valid grade level between 1 and 12.")
        ],
    )
    
    def __str__(self):
        return f"{self.user.get_first_name()} ({self.user.email})"


# Invite model
class Invite(models.Model):
    # Invite status choices
    INVITE_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    )

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="invites"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="sent_invites"
    )
    status = models.CharField(
        max_length=10, choices=INVITE_STATUS_CHOICES, default="pending"
    )
    message = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "teacher")

    def __str__(self):
        return f"Invite from {self.teacher} to {self.student} ({self.status})"

```

# --- File: cs_nea/users/__init__.py ---

```python

```

# --- File: cs_nea/users/apps.py ---

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

```

# --- File: cs_nea/users/forms.py ---

```python
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Student, Teacher, Invite
from communications.models import Note
from phonenumber_field.formfields import SplitPhoneNumberField

# Login form
class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

# Signup form
class SignupForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    contact_number = SplitPhoneNumberField()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "confirm_password",
            "contact_number",
            "date_of_birth",
        ]
        widgets = {
            "password": forms.PasswordInput(),
            "date_of_birth": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
    
    # Validations
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match")
            try:
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error("password", error)

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists")
        return email

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth:
            from datetime import date

            age = (date.today() - date_of_birth).days // 365
            if age < 10:
                raise ValidationError(
                    "You must be at least 10 years old to register. Please have your parent or guardian register for you."
                )
        return date_of_birth


# Student signup form
class StudentSignupForm(SignupForm):
    grade_level = forms.IntegerField(
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Enter a grade level between 1 and 12.",
        label="Grade Level",
    )
    extra_student_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        label="Extra Information About You (Optional)",
    )

    class Meta(SignupForm.Meta):
        model = User
        fields = SignupForm.Meta.fields + ["grade_level", "extra_student_info"]

# Teacher signup form
class TeacherSignupForm(SignupForm):
    extra_teacher_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        label="Extra Information About You (Optional)",
    )

    class Meta(SignupForm.Meta):
        model = User
        fields = SignupForm.Meta.fields + ["extra_teacher_info"]


# 2-FA form
class TwoFactorForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )


# Account retrieval forms
class RetrieveAccountForm(forms.Form):
    email = forms.EmailField()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()

# Password reset form
class PasswordResetForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(), validators=[validate_password]
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match")

        return cleaned_data


# FIXME: Some fields should be greyed out and non-editable
class UserSettingsForm(forms.ModelForm):
    current_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    new_password = forms.CharField(
        widget=forms.PasswordInput(), required=False, validators=[validate_password]
    )
    confirm_new_password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "two_factor_enabled",
        ]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "disabled": "disabled",
                    "class": "bg-neutral-200"
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "disabled": "disabled",
                    "class": "bg-neutral-200"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "disabled": "disabled",
                    "class": "bg-neutral-200"
                }
            ),
        }
     # Validation
    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")

        if new_password:
            if not current_password:
                raise forms.ValidationError(
                    "Current password is required to set a new password"
                )
            if new_password != confirm_new_password:
                raise forms.ValidationError("New passwords do not match")

        return cleaned_data


# Invite form
class InviteForm(forms.Form):
    student_email = forms.EmailField(label="Student's Email")
    message = forms.CharField(widget=forms.Textarea, max_length=500, required=False)

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop("teacher", None)
        super(InviteForm, self).__init__(*args, **kwargs)

    def clean_student_email(self):
        email = self.cleaned_data["student_email"]
        try:
            user = User.objects.get(email=email, user_type=1)  # 1 is for Student
            student = user.student

            # Check if an invite from this teacher already exists
            existing_invite = Invite.objects.filter(
                student=student, teacher=self.teacher
            ).first()
            if existing_invite:
                if existing_invite.status == "accepted":
                    raise ValidationError(
                        "You are already connected with this student."
                    )
                elif existing_invite.status == "pending":
                    raise ValidationError(
                        "You have already sent an invite to this student."
                    )
                    
        # Error checking and validation
        except User.DoesNotExist:
            raise ValidationError("No student account found with this email address.")
        return email


# Form to implement notes
class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["note_content"]
        widgets = {
            "note_content": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

```

# --- File: cs_nea/users/admin.py ---

```python
from django.contrib import admin

# Register your models here.

```

# --- File: cs_nea/users/urls.py ---

```python
from django.urls import path
from .views import (
    index,
    login,
    signup,
    logout,
    profile,
    settings,
    two_factor_verify,
    account_recovery,
    password_reset_request,
    password_reset,
    invite_student,
    student_invites,
    accept_invite,
    teacher_students,
    student_teachers,
)

urlpatterns = [
    path("", index, name="index"),
    path("logout", logout, name="logout"),
    path("student/login", login, name="student_login"),
    path("teacher/login", login, name="teacher_login"),
    path("student/signup", signup, name="student_signup"),
    path("teacher/signup", signup, name="teacher_signup"),
    path("profile", profile, name="user_profile"),
    path("settings", settings, name="settings"),
    # URL for two-factor authentication verification before login, only if 2FA activated in settings
    path("two_factor_verify", two_factor_verify, name="two_factor_verify"),
    path("account_recovery", account_recovery, name="account_recovery"),
    path(
        "password_reset_request", password_reset_request, name="password_reset_request"
    ),
    # Password reset token is passed as a URL parameter, URL only accessed through emailed link
    path('password_reset/<str:token>/', password_reset, name='password_reset'),
    
    # Invite related URLs
    path('invite_student/', invite_student, name='invite_student'),
    path('student_invites/', student_invites, name='student_invites'),
    path('accept_invite/<int:invite_id>/', accept_invite, name='accept_invite'),
    # Notes URLs         
    path('teacher_students/', teacher_students, name='teacher_students'),
    path('student_teachers/', student_teachers, name='student_teachers'),
]

```

# --- File: cs_nea/users/views.py ---

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from datetime import timedelta
from .forms import (
    LoginForm,
    SignupForm,
    StudentSignupForm,
    TeacherSignupForm,
    TwoFactorForm,
    RetrieveAccountForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    UserSettingsForm,
    InviteForm,
    NoteForm,
)
from .models import Student, Teacher, User, Invite
from communications.models import Note


def index(request):
    return render(request, "index.html")

# Login view
def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)
            # Checks if the user account is valid, then redirects to dashboard
            if user is not None:
                if 'teacher/login' in request.path:
                    if not user.user_type == 2:
                        messages.error(request, "This is not a teacher account")
                        return redirect("teacher_login")
                elif 'student/login' in request.path:
                    if not user.user_type == 1:
                        messages.error(request, "This is not a student account")
                        return redirect("student_login")

                if user.two_factor_enabled:
                    user.generate_two_factor_code()
                    send_two_factor_code(user)
                    request.session["user_id"] = user.id
                    return redirect("two_factor_verify")
                else:
                    auth_login(request, user)
                    messages.success(request, "You have successfully logged in.")
                    return redirect("dashboard")
            else:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


# 2-FA views
def two_factor_verify(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("index")

    user = User.objects.get(id=user_id)

    # Checks if the code is valid and not expired
    if request.method == "POST":
        form = TwoFactorForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get("code")
            if (
                user.two_factor_code == code
                and user.two_factor_code_expiry > timezone.now()
            ):
                auth_login(request, user)
                user.two_factor_code = None
                user.two_factor_code_expiry = None
                user.save()
                messages.success(request, "You have successfully logged in.")
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid or expired code")
    else:
        form = TwoFactorForm()

    return render(request, "users/two_factor_verify.html", {"form": form})


# Account recovery views
def account_recovery(request):
    if request.method == "POST":
        form = RetrieveAccountForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = User.objects.get(email=email)
                send_password_reset_link(request, user)
                messages.success(
                    request, "A password reset link has been sent to your email."
                )
                return redirect("index")
            except User.DoesNotExist:
                messages.error(request, "No account found with this email address.")
    else:
        form = RetrieveAccountForm()

    return render(request, "users/account_recovery.html", {"form": form})


# Sends a two-factor authentication code to the user's email
def send_two_factor_code(user):
    subject = "Your Two-Factor Authentication Code"
    message = f"Your two-factor authentication code is: {user.two_factor_code}"
    send_mail(subject, message, "noreply@example.com", [user.email])


# Account retrieval views
def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = User.objects.get(email=email)
                user.generate_password_reset_token()
                send_password_reset_link(request, user)
                messages.success(
                    request, "A password reset link has been sent to your email."
                )
                return redirect("index")
            except User.DoesNotExist:
                messages.error(request, "No account found with this email address.")
    else:
        form = PasswordResetRequestForm()

    return render(request, "users/password_reset_request.html", {"form": form})


def password_reset(request, token):
    user = get_object_or_404(User, password_reset_token=token)

    # Check if the token has expired (e.g., after 24 hours)
    if user.password_reset_token_created_at < timezone.now() - timedelta(hours=24):
        messages.error(
            request, "The password reset link has expired. Please request a new one."
        )
        return redirect("password_reset_request")

    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get("new_password")
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()
            messages.success(request, "Your password has been reset successfully.")
            return redirect("index")
    else:
        form = PasswordResetForm()

    return render(request, "users/password_reset.html", {"form": form})


# Enables or disables 2-FA for future logins
@login_required
def enable_disable_2fa(request):
    user = request.user
    if request.method == "POST":
        form = EnableDisable2FAForm(request.POST)
        if form.is_valid():
            enable_2fa = form.cleaned_data.get("enable_2fa")
            user.two_factor_enabled = enable_2fa
            user.save()
            if enable_2fa:
                messages.success(request, "Two-factor authentication has been enabled.")
            else:
                messages.success(
                    request, "Two-factor authentication has been disabled."
                )
            return redirect("settings")
    else:
        form = EnableDisable2FAForm(initial={"enable_2fa": user.two_factor_enabled})

    return render(request, "users/enable_disable_2fa.html", {"form": form})


# Sends a password reset link to the user's email
def send_password_reset_link(request, user):
    user.generate_password_reset_token()
    reset_link = request.build_absolute_uri(
        reverse("password_reset", args=[user.password_reset_token])
    )
    subject = "Password Reset Link"
    message = f"Click the following link to reset your password: {reset_link}"
    send_mail(subject, message, "noreply@example.com", [user.email])


# Signup views
def signup(request):
    if request.path == "/student/signup":
        form_class = StudentSignupForm
        user_type = 1
    elif request.path == "/teacher/signup":
        form_class = TeacherSignupForm
        user_type = 2
    else:
        return redirect("index")

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data["password"])
                    user.user_type = user_type
                    user.save()

                    if user_type == 1:  # Student
                        Student.objects.create(
                            user=user,
                            grade_level=form.cleaned_data["grade_level"],
                            extra_student_info=form.cleaned_data.get("extra_student_info", "")
                        )
                    elif user_type == 2:  # Teacher
                        Teacher.objects.create(
                            user=user,
                            extra_teacher_info=form.cleaned_data.get("extra_teacher_info", "")
                        )

                messages.success(request, "Your account has been successfully created!")
                return redirect("student_login" if user_type == 1 else "teacher_login")
            except Exception as e:
                messages.error(request, f"An error occurred during signup: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = form_class()

    return render(request, "users/signup.html", {"form": form})


def logout(request):
    auth_logout(request)
    return redirect("index")


def profile(request):
    return render(request, "users/profile.html")


# Settings views
@login_required
def settings(request):
    user = request.user
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=user)
        if form.is_valid():
            if form.cleaned_data.get("new_password"):
                if user.check_password(form.cleaned_data.get("current_password")):
                    user.set_password(form.cleaned_data.get("new_password"))
                    update_session_auth_hash(request, user)  # Keep the user logged in
                    messages.success(request, "Your password has been updated.")
                else:
                    messages.error(request, "Current password is incorrect.")
                    return render(request, "users/settings.html", {"form": form})

            form.save()
            messages.success(request, "Your settings have been updated.")
            return redirect("settings")
    else:
        form = UserSettingsForm(instance=user)

    return render(request, "users/settings.html", {"form": form})


# Invite views
@login_required
@user_passes_test(lambda u: u.user_type == 2)
def invite_student(request):
    teacher = request.user.teacher
    if request.method == "POST":
        form = InviteForm(request.POST, teacher=teacher)
        # Validates form and creates an invite
        if form.is_valid():
            student_email = form.cleaned_data["student_email"]
            message = form.cleaned_data["message"]
            
            student_user = User.objects.get(email=student_email, user_type=1)
            student = student_user.student

            invite, created = Invite.objects.get_or_create(
                student=student,
                teacher=teacher,
                defaults={"message": message, "status": "pending"},
            )

            if created:
                messages.success(request, f"Invite sent to {student_email}")
            else:
                messages.info(request, f"Invite already sent to {student_email}")

            return redirect("teacher_dashboard")
    else:
        form = InviteForm(teacher=teacher)

    return render(request, "users/teacher_templates/invite_student.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.user_type == 1)
def student_invites(request):
    student = request.user.student
    pending_invites = Invite.objects.filter(student=student, status="pending")
    return render(request, "users/student_templates/student_invites.html", {"invites": pending_invites})


@login_required
@user_passes_test(lambda u: u.user_type == 1)
def accept_invite(request, invite_id):
    invite = get_object_or_404(
        Invite, id=invite_id, student=request.user.student, status="pending"
    )
    invite.status = "accepted"
    invite.save()
    messages.success(
        request, f"You are now connected with {invite.teacher.user.get_full_name()}"
    )
    return redirect("student_dashboard")


# Views for notes
@login_required
@user_passes_test(lambda u: u.user_type == 1)
def student_teachers(request):
    student = request.user.student
    accepted_invites = Invite.objects.filter(student=student, status="accepted")
    teachers = [invite.teacher for invite in accepted_invites]
    return render(request, "users/student_templates/student_teachers.html", {"teachers": teachers})


# Views for teachers view of their students and notes
@login_required
@user_passes_test(lambda u: u.user_type == 2)
def teacher_students(request):
    teacher = request.user.teacher
    accepted_invites = Invite.objects.filter(teacher=teacher, status="accepted")
    students = [invite.student for invite in accepted_invites]
    notes = Note.objects.filter(teacher=teacher)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_note':
            form = NoteForm(request.POST)
            if form.is_valid():
                note = form.save(commit=False)
                note.teacher = teacher
                note.student_id = request.POST.get('student_id')
                note.save()
                messages.success(request, 'Note added successfully.')
            else:
                messages.error(request, 'Error adding note. Please try again.')
        elif action == 'edit_note':
            note_id = request.POST.get('note_id')
            note = get_object_or_404(Note, note_id=note_id, teacher=teacher)
            form = NoteForm(request.POST, instance=note)
            if form.is_valid():
                form.save()
                messages.success(request, 'Note updated successfully.')
            else:
                messages.error(request, 'Error updating note. Please try again.')
        elif action == 'delete_note':
            note_id = request.POST.get('note_id')
            note = get_object_or_404(Note, note_id=note_id, teacher=teacher)
            note.delete()
            messages.success(request, 'Note deleted successfully.')

        return redirect('teacher_students')

    context = {
        'students': students,
        'notes': notes,
        'form': NoteForm(),
    }
    return render(request, 'users/teacher_templates/teacher_students.html', context)





```

# === Directory: cs_nea/templates ===


# --- File: cs_nea/templates/index.html ---

```html
{% extends "_base.html" %}

<!-- Home page -->
{% block content %}
<div class="">
  <div class="bg-gradient-to-b from-purple-500 to-blue-900">
    <div class="flex flex-col flex-auto items-center justify-center h-svh">
      <p class="p-5 text-5xl font-bold text-white">MusBook</p>
      <p class="text-xl text-white">Music lesson scheduling made easy</p>

      {% if not user.is_authenticated %}
      <div class="p-10">
        <a href="{% url 'student_login' %}" class="px-4">
          <button
            type="button"
            class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 hover:ring-neutral-500 shadow-lg"
          >
            Students
          </button>
        </a>
        <a href="{% url 'teacher_login' %}" class="px-4">
          <button
            type="button"
            class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 hover:ring-neutral-500 shadow-lg"
          >
            Teachers
          </button>
        </a>
      </div>
      {% endif %}
    </div>
  </div>
  
</div>
{% endblock content %}

```

# --- File: cs_nea/templates/_dashboard.html ---

```html
<!-- TODO: Make dashboard more responsive -->

{% load static %} {% load static tailwind_tags %}

<!-- Dashboard template for after user has logged in -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEA</title>
    {% tailwind_css %}
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
    {% block extra_head %}{% endblock %}
    <style>
        #sidebar {
            transition: transform 0.3s ease-in-out;
        }
    </style>
</head>
<body class="bg-neutral-200" x-data="sidebarData()" x-init="init()">
    <div>
        <header class="sticky top-0 z-50">
            <div class="flex fixed top-0 py-2 w-full items-center justify-between bg-neutral-800 bg-opacity-95 backdrop-blur shadow-md">
                <!-- Left -->
                <div class="flex flex-grow gap-x-10 px-10 text-lg text-white py-2.5">
                    {% if "home" in request.path %}
                    <div class="flex font-semibold">
                        <a href="{% url 'index' %}" class="hover:text-purple-400">Home</a>
                    </div>
                    {% endif %}
                    <!-- Sidebar Button -->
                    {% if user.is_authenticated %}
                    <button @click="toggleSidebar()" class="text-white focus:outline-none">
                        <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 6H20M4 12H20M4 18H11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                        </svg>
                    </button>
                    <div class="flex">
                        <a href="{% url 'dashboard' %}" class="hover:text-purple-400">Dashboard</a>
                    </div>
                    {% endif %}
                </div>

                <!-- Auto disappearing messages -->
                <div id="messages-container" class="fixed left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md px-4">
                    <div class="w-full pt-2">
                        {% for message in messages %}
                        <div class="message px-4 py-3 rounded-md shadow-sm mb-2 flex items-center justify-between {% if message.tags == 'error' %} bg-red-100 border border-red-400 text-red-700 {% else %} bg-green-100 border border-green-400 text-green-700 {% endif %}" role="alert">
                            <span class="flex-grow">{{ message }}</span>
                            <button onclick="dismissMessage(this.parentNode)" class="ml-4 focus:outline-none">
                                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                                </svg>
                            </button>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <script>
                    document.addEventListener("DOMContentLoaded", function () {
                        const messages = document.querySelectorAll("#messages-container .message");
                        messages.forEach((message) => {
                            setTimeout(() => {
                                dismissMessage(message);
                            }, 10000);
                        });
                    });

                    function dismissMessage(messageElement) {
                        messageElement.style.transition = "opacity 300ms, transform 300ms";
                        messageElement.style.opacity = "0";
                        messageElement.style.transform = "scale(0.9)";
                        setTimeout(() => {
                            messageElement.remove();
                        }, 300);
                    }
                </script>

                <!-- Right -->
                <div class="flex gap-x-6 px-6">
                    {% block navright %}{% endblock navright %}
                    {% if user.is_authenticated %}
                    <!-- Notification component -->
                    {% include "components/notification.html" %}
                    <!-- Current user component -->
                    {% include "components/current_user.html" %}
                    {% endif %}
                </div>
            </div>
        </header>

        <main class="relative">
            <!-- Content | Below is dashboard only code -->
            <div class="flex h-screen bg-gray-200">
                <!-- Sidebar -->
                <div id="sidebar" class="z-30 inset-y-0 left-0 w-56 transform bg-neutral-700 overflow-y-auto fixed top-14 transition" :class="{'translate-x-0 ease-out': sidebarOpen, '-translate-x-full ease-in': !sidebarOpen}">
                    <!-- Sidebar content -->
                    <a href="{% url 'calendar' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Calendar</span>
                    </a>
                    {% if user.user_type == 1 %}
                    <a href="{% url 'student_invites' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">View Invites</span>
                    </a>
                    <a href="{% url 'student_teachers' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">My Teachers</span></a>
                    <a href="{% url 'student_lesson_request' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Schedule with a teacher</span></a>
                    {% elif user.user_type == 2 %}
                    <a href="{% url 'invite_student' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Invite Student</span></a>
                    <a href="{% url 'teacher_students' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">My Students</span></a>
                    <a href="{% url 'teacher_lesson_request' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Schedule with a student</span></a>
                    {% endif %}
                    <a href="{% url 'reschedule_lesson' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Reschedule a lesson</span></a>
                    <a href="{% url 'message_list' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Messages</span></a>
                    <a href="{% url 'assignment_list' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Assignments</span></a>
                    <a href="{% url 'lesson_requests' %}" class="flex items-center mt-4 py-2 px-6 text-white hover:bg-neutral-800 hover:bg-opacity-25 sidebar-link">
                        <span class="mx-3">Lesson Requests</span></a>
                    {% block sidemenu %}{% endblock %}
                </div>

                <!-- Main content -->
                <div class="flex-1 flex flex-col overflow-hidden" :class="{'ml-64': sidebarOpen, 'ml-0': !sidebarOpen}">
                    <div class="flex-1 flex flex-col overflow-hidden bg-gray-200 pt-20">
                        <div class="flex-1 flex flex-col overflow-hidden container mx-auto px-4">
                            <h3 class="text-neutral-800 text-3xl mb-8 font-bold">
                                {% block name %}{% endblock %}
                            </h3>
                            <!-- Add dashboard content here... -->
                            <div class="flex-1 overflow-y-auto mb-2">
                                {% block content %}{% endblock %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        function sidebarData() {
            return {
                sidebarOpen: localStorage.getItem('sidebarOpen') === 'true',
                init() {
                    this.$watch('sidebarOpen', value => {
                        localStorage.setItem('sidebarOpen', value);
                    });
                    document.addEventListener('mousemove', this.handleMouseMove.bind(this));
                },
                handleMouseMove(event) {
                    const sidebarWidth = document.querySelector('#sidebar').offsetWidth;
                    const mouseX = event.clientX;

                    if (mouseX <= 10) {
                        this.sidebarOpen = true;
                    } else if (mouseX > sidebarWidth) {
                        this.sidebarOpen = false;
                    }
                },
                toggleSidebar() {
                    this.sidebarOpen = !this.sidebarOpen;
                }
            };
        }

        document.addEventListener('alpine:init', () => {
            Alpine.data('sidebarData', sidebarData);
        });
    </script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>

```

# --- File: cs_nea/templates/_base.html ---

```html
{% load static %} {% load static tailwind_tags %}
<!-- Base template for all pages -->
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta http-equiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>NEA</title>
        {% tailwind_css %}
        <script
            defer
            src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"
        ></script>
    </head>

    <body class="bg-neutral-200" x-data="{ sidebarOpen: true }">
        <div>
            <header class="sticky top-0 z-50">
                <div
                    class="flex fixed top-0 py-2 w-full items-center justify-between bg-neutral-800 bg-opacity-95 backdrop-blur shadow-md"
                >
                    <!-- Left -->
                    <div
                        class="flex flex-grow gap-x-10 px-10 text-lg text-white py-2.5"
                    >
                        {% if "home" or "password_reset" in request.path %}
                        <div class="flex font-semibold">
                            <a
                                href="{% url 'index' %}"
                                class="hover:text-purple-400"
                                >Home</a
                            >
                        </div>
                        {% endif %} {% block navleft %}{% endblock navleft %} {% if user.is_authenticated %}
                        <div class="flex">
                            <a
                                href="{% url 'dashboard' %}"
                                class="hover:text-purple-400"
                                >Dashboard</a
                            >
                        </div>
                        {% endif %}
                    </div>

                    <!-- Auto dissapearing messages -->
                    <div
                        id="messages-container"
                        class="fixed left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md px-4"
                    >
                        <div class="w-full pt-2">
                            {% for message in messages %}
                            <div
                                class="message px-4 py-3 rounded-md shadow-sm mb-2 flex items-center justify-between {% if message.tags == 'error' %} bg-red-100 border border-red-400 text-red-700 {% else %} bg-green-100 border border-green-400 text-green-700 {% endif %}"
                                role="alert"
                            >
                                <span class="flex-grow">{{ message }}</span>
                                <button
                                    onclick="dismissMessage(this.parentNode)"
                                    class="ml-4 focus:outline-none"
                                >
                                    <svg
                                        class="h-5 w-5"
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                    >
                                        <path
                                            fill-rule="evenodd"
                                            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                                            clip-rule="evenodd"
                                        />
                                    </svg>
                                </button>
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                    <script>
                        document.addEventListener(
                            "DOMContentLoaded",
                            function () {
                                const messages = document.querySelectorAll(
                                    "#messages-container .message"
                                );
                                messages.forEach((message) => {
                                    setTimeout(() => {
                                        dismissMessage(message);
                                    }, 10000);
                                });
                            }
                        );

                        function dismissMessage(messageElement) {
                            messageElement.style.transition =
                                "opacity 300ms, transform 300ms";
                            messageElement.style.opacity = "0";
                            messageElement.style.transform = "scale(0.9)";
                            setTimeout(() => {
                                messageElement.remove();
                            }, 300);
                        }
                    </script>
                
                    <!-- Right -->
                    <div class="flex gap-x-6 px-6">
                        {% block navright %}{% endblock navright %} 
                        {% if user.is_authenticated %}
                        <div
                            x-data="{ open: false }"
                            class="relative inline-block text-left mr-4"
                        >
                            <div>
                                <button
                                    @click="open = !open"
                                    type="button"
                                    class="inline-flex justify-center w-full rounded-md shadow-sm px-4 py-2 bg-purple-500 text-sm font-medium text-white hover:bg-purple-600 ring-purple-800"
                                    id="options-menu"
                                    aria-haspopup="true"
                                    x-bind:aria-expanded="open"
                                >
                                    {{ user.first_name }} {{ user.last_name }}
                                    <svg
                                        class="-mr-1 ml-2 h-5 w-5"
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                        aria-hidden="true"
                                    >
                                        <path
                                            fill-rule="evenodd"
                                            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                            clip-rule="evenodd"
                                        />
                                    </svg>
                                </button>
                            </div>

                            <div
                                x-show="open"
                                @click.away="open = false"
                                class="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-neutral-100"
                            >
                                <div
                                    class="py-1"
                                    role="menu"
                                    aria-orientation="vertical"
                                    aria-labelledby="options-menu"
                                >
                                    <a
                                        href="{% url 'settings' %}"
                                        class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                                        role="menuitem"
                                        >Settings</a
                                    >
                                    <a
                                        href="{% url 'user_profile' %}"
                                        class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                                        role="menuitem"
                                        >Profile</a
                                    >
                                    <a
                                        href="{% url 'logout' %}"
                                        class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                                        role="menuitem"
                                        >Log out</a
                                    >
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </header>

            <main class="relative">
                <!-- Content -->
                {% block content %} {% endblock content %}
            </main>

            <footer></footer>
        </div>

        <script
            defer
            src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"
        ></script>
    </body>
</html>

```

# === Directory: cs_nea/templates/scheduling ===


# --- File: cs_nea/templates/scheduling/lesson_requests.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block name %}Lesson Requests{% endblock %}

{% block content %}
<!-- View for lesson request -->
<div class="container mx-auto" x-data="{ showAcceptModal: false, showDeclineModal: false, selectedRequest: null, requestType: '' }">
    {% if scheduling_requests or rescheduling_requests %}
        <h2 class="text-xl font-semibold mb-4">New Lesson Requests</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {% for request in scheduling_requests %}
                <div class="bg-white shadow-md rounded-lg p-6">
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">New Lesson Request</h3>
                    {% if user.user_type == 1 %}
                        <p>From: {{ request.teacher.user.get_full_name }}</p>
                    {% else %}
                        <p>From: {{ request.student.user.get_full_name }}</p>
                    {% endif %}
                    <p>Start: <span class="datetime" data-datetime="{{ request.requested_datetime|date:'c' }}"></span></p>
                    <p>End: <span class="datetime" data-datetime="{{ request.end_datetime|date:'c' }}"></span></p>
                    <p>Recurring: {{ request.recurring_amount }} time(s)</p>
                    <p>Reason: {{ request.request_reason }}</p>
                    <div class="flex justify-between mt-4">
                        <button @click="showAcceptModal = true; selectedRequest = '{{ request.request_id }}'; requestType = 'schedule'" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded">
                            Accept
                        </button>
                        <button @click="showDeclineModal = true; selectedRequest = '{{ request.request_id }}'; requestType = 'schedule'" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded">
                            Decline
                        </button>
                    </div>
                </div>
            {% endfor %}
        </div>

        <h2 class="text-xl font-semibold mb-4">Rescheduling Requests</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {% for request in rescheduling_requests %}
                <div class="bg-white shadow-md rounded-lg p-6">
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">Rescheduling Request</h3>
                    {% if user.user_type == 1 %}
                        <p>From: {{ request.original_lesson.teacher.user.get_full_name }}</p>
                    {% else %}
                        <p>From: {{ request.original_lesson.student.user.get_full_name }}</p>
                    {% endif %}
                    <p>Original Lesson: <span class="datetime" data-datetime="{{ request.original_lesson.start_datetime|date:'c' }}"></span></p>
                    <p>New Start: <span class="datetime" data-datetime="{{ request.requested_datetime|date:'c' }}"></span></p>
                    <p>New End: <span class="datetime" data-datetime="{{ request.end_datetime|date:'c' }}"></span></p>
                    <p>Reason: {{ request.request_reason }}</p>
                    <div class="flex justify-between mt-4">
                        <button @click="showAcceptModal = true; selectedRequest = '{{ request.rescheduling_id }}'; requestType = 'reschedule'" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded">
                            Accept
                        </button>
                        <button @click="showDeclineModal = true; selectedRequest = '{{ request.rescheduling_id }}'; requestType = 'reschedule'" class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded">
                            Decline
                        </button>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <p class="text-xl">No pending lesson requests.</p>
    {% endif %}

    <!-- Accept Modal -->
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full" x-show="showAcceptModal" x-cloak>
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3 text-center">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Confirm Acceptance</h3>
                <div class="mt-2 px-7 py-3">
                    <p class="text-sm text-gray-500">Are you sure you want to accept this lesson request?</p>
                </div>
                <div class="items-center px-4 py-3">
                    <button @click="showAcceptModal = false" class="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md w-24 mr-2 hover:bg-gray-600">
                        Cancel
                    </button>
                    <a :href="requestType === 'schedule' ? '/accept_lesson_request/' + selectedRequest + '/' : '/accept_rescheduling_request/' + selectedRequest + '/'" 
                       class="px-4 py-2 bg-green-500 text-white text-base font-medium rounded-md w-24 hover:bg-green-600">
                        Confirm
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Decline Modal -->
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full" x-show="showDeclineModal" x-cloak>
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3 text-center">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Confirm Decline</h3>
                <div class="mt-2 px-7 py-3">
                    <p class="text-sm text-gray-500">Are you sure you want to decline this lesson request?</p>
                </div>
                <div class="items-center px-4 py-3">
                    <button @click="showDeclineModal = false" class="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md w-24 mr-2 hover:bg-gray-600">
                        Cancel
                    </button>
                    <a :href="requestType === 'schedule' ? '/decline_lesson_request/' + selectedRequest + '/' : '/decline_rescheduling_request/' + selectedRequest + '/'" 
                       class="px-4 py-2 bg-red-500 text-white text-base font-medium rounded-md w-24 hover:bg-red-600">
                        Confirm
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Converts UTC time from db to local time -->
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const dateTimeElements = document.querySelectorAll('.datetime');
        dateTimeElements.forEach(element => {
            const dateTimeString = element.getAttribute('data-datetime');
            const localDate = new Date(dateTimeString);
            const options = {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true,
            };
            element.textContent = localDate.toLocaleDateString(undefined, options);
        });
    });
</script>
{% endblock %}

```

# --- File: cs_nea/templates/scheduling/calendar.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
{% endblock %}

{% block name %}Calendar{% endblock %}

{% block content %}

<div class="bg-white rounded-lg shadow-md p-6 h-full">
    <div class="h-full flex flex-col overflow-hidden">
        <div class="flex-grow overflow-y-auto">
            <div class="container mx-auto p-4 h-full">
                <div class="bg-white shadow-md rounded-lg overflow-hidden h-full">
                    <div id="calendar" class="h-full"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal for confirmation -->
<div id="eventModal" class="fixed inset-0 z-50 overflow-y-auto hidden bg-black bg-opacity-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-8 m-4 max-w-xl w-full">
            <h2 id="modalTitle" class="text-xl mb-4"></h2>
            <form id="eventForm">
                {% csrf_token %}
                <input type="hidden" id="eventId" name="id">
                <div class="mb-4">
                    <label for="eventTitle" class="block text-sm font-medium text-gray-700">Event Title</label>
                    <input type="text" id="eventTitle" name="title" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventAllDay" class="flex items-center">
                        <input type="checkbox" id="eventAllDay" name="allDay" class="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                        <span class="ml-2 text-sm text-gray-700">All Day</span>
                    </label>
                </div>
                <div class="mb-4">
                    <label for="eventStart" class="block text-sm font-medium text-gray-700">Start Time</label>
                    <input type="datetime-local" id="eventStart" name="start" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventEnd" class="block text-sm font-medium text-gray-700">End Time</label>
                    <input type="datetime-local" id="eventEnd" name="end" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="flex justify-end space-x-2">
                    <button type="button" onclick="closeModal()" class="px-4 py-2 bg-gray-300 text-black rounded hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50">Cancel</button>
                    <button type="button" id="deleteEventButton" class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50">Delete</button>
                    <button type="button" id="saveEventButton" onclick="saveEvent()" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50">Save</button>

                </div>
            </form>
        </div>
    </div>
</div>


<script>
    // Calendar Initialization
    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('calendar');
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: '/get_calendar_data/',
            selectable: true,
            select: handleDateSelect,
            eventClick: function(info) {
                if (info.event.id.startsWith('event_')) {
                    showEditModal(info.event, false);
                } else if (info.event.id.startsWith('lesson_')) {
                    showEditModal(info.event, true);
                }
            },
            
            eventDrop: function(info) {
                updateEvent(info.event);
            },
            eventResize: function(info) {
                updateEvent(info.event);
            },
            height: '100%',
            timeZone: 'local',
            fixedWeekCount: false, 
        });
    
        calendar.render();
    });

    function handleDateSelect(selectInfo) {
        var allDay = !selectInfo.view.type.includes('time');
        var start = selectInfo.start;
        var end = selectInfo.end;
    
        if (allDay) {
            // For all-day event subtract one day
            end = new Date(end.getTime() - 86400000);
        }
    
        showModal('Create Event', start, end, allDay);
    }

    function formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    function formatDateTime(date) {
        return date.toISOString().slice(0, 16);
    }
    
    function showModal(title, start, end, allDay) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('eventTitle').value = '';
        document.getElementById('eventAllDay').checked = allDay;
    
        var startDate = moment(start);
        var endDate = moment(end);
    
        // Temporarily change the type to text to ensure re-rendering - Fixes issue where on first time fields aren't populated
        document.getElementById('eventStart').type = 'text';
        document.getElementById('eventEnd').type = 'text';
    
        if (allDay) {
            document.getElementById('eventStart').value = startDate.format('YYYY-MM-DD');
            document.getElementById('eventEnd').value = endDate.format('YYYY-MM-DD');
            document.getElementById('eventStart').type = 'date';
            document.getElementById('eventEnd').type = 'date';
        } else {
            document.getElementById('eventStart').value = startDate.format('YYYY-MM-DDTHH:mm');
            document.getElementById('eventEnd').value = endDate.format('YYYY-MM-DDTHH:mm');
            document.getElementById('eventStart').type = 'datetime-local';
            document.getElementById('eventEnd').type = 'datetime-local';
        }
    
        document.getElementById('eventId').value = '';
        document.getElementById('eventModal').classList.remove('hidden');
        updateDateTimeInputs(allDay);
    }
    
    
    function showEditModal(event, isLesson) {
        document.getElementById('modalTitle').textContent = isLesson ? 'View Lesson' : 'Edit Event';
        document.getElementById('eventTitle').value = event.title;
        document.getElementById('eventAllDay').checked = event.allDay;
        document.getElementById('eventId').value = event.id;

        // Temporarily change the type to text to ensure re-rendering - Fixes issue where on first time fields aren't populated
        document.getElementById('eventStart').type = 'text';
        document.getElementById('eventEnd').type = 'text';
    
        // Convert UTC to local time
        let startLocal = moment.utc(event.start).local().format('YYYY-MM-DDTHH:mm');
        let endLocal = moment.utc(event.end).local().format('YYYY-MM-DDTHH:mm');
    
        if (event.allDay) {
            document.getElementById('eventStart').value = startLocal.slice(0, 10);
            document.getElementById('eventEnd').value = endLocal.slice(0, 10);
        } else {
            document.getElementById('eventStart').value = startLocal;
            document.getElementById('eventEnd').value = endLocal;
        }
    
        // Disable fields if it's a lesson
        document.getElementById('eventTitle').disabled = isLesson;
        document.getElementById('eventAllDay').disabled = isLesson;
        document.getElementById('eventStart').disabled = isLesson;
        document.getElementById('eventEnd').disabled = isLesson;
    
        // Hide delete and save buttons if it's a lesson
        document.getElementById('deleteEventButton').style.display = isLesson ? 'none' : 'inline-block';
        document.getElementById('saveEventButton').style.display = isLesson ? 'none' : 'inline-block';
    
        document.getElementById('eventModal').classList.remove('hidden');
        updateDateTimeInputs(event.allDay);
    }
    
    
    
    function closeModal() {
        document.getElementById('eventModal').classList.add('hidden');
    }
    
    function updateDateTimeInputs(allDay) {
        var startInput = document.getElementById('eventStart');
        var endInput = document.getElementById('eventEnd');
        if (allDay) {
            startInput.type = 'date';
            endInput.type = 'date';
        } else {
            startInput.type = 'datetime-local';
            endInput.type = 'datetime-local';
        }
    }
    
    function saveEvent() {
        var form = document.getElementById('eventForm');
        var formData = new FormData(form);
        var eventId = formData.get('id');
        var url = eventId ? '/update_event/' : '/create_event/';

        var allDay = document.getElementById('eventAllDay').checked;
        formData.set('allDay', allDay);

        var start = formData.get('start');
        var end = formData.get('end');
 
        if (allDay) {
            // For all-day events, use the date and set time to midnight UTC
            start = moment(start).format('YYYY-MM-DD');
            end = moment(end).format('YYYY-MM-DD');
        } else {
            // For timed events, keep the time but ensure it's in ISO format
            start = moment(start).subtract(timezoneOffset, 'minutes').format('YYYY-MM-DDTHH:mm:ss');
            end = moment(end).subtract(timezoneOffset, 'minutes').format('YYYY-MM-DDTHH:mm:ss');
        }

        formData.set('start', start);
        formData.set('end', end);

        // Add timezone offset
        var timezoneOffset = new Date().getTimezoneOffset();
        formData.set('timezone_offset', timezoneOffset);
    
        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                closeModal();
                if (eventId) {
                    var existingEvent = calendar.getEventById(eventId);
                    if (existingEvent) {
                        existingEvent.remove();
                    }
                }
                calendar.addEvent(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving the event.');
        });
    }
    
    function updateEvent(event) {
        var formData = new FormData();
        formData.append('id', event.id);
        formData.append('title', event.title);
        
        var start, end;
        if (event.allDay) {
            // For all-day events, adjust the end date
            start = moment(event.start).format('YYYY-MM-DD');
            end = moment(event.end).subtract(1, 'days').format('YYYY-MM-DD');
        } else {
            start = moment(event.start).format('YYYY-MM-DDTHH:mm:ss');
            end = moment(event.end).format('YYYY-MM-DDTHH:mm:ss');
        }
        
        formData.append('start', start);
        formData.append('end', end);
        formData.append('allDay', event.allDay);
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
        
        // Add timezone offset
        formData.append('timezone_offset', new Date().getTimezoneOffset());
    
        fetch('/update_event/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                event.revert();
            } else {
                // Update successful
            }
        })
        .catch(error => {
            console.error('Error:', error);
            event.revert();
        });
    }

    function deleteEvent() {
        var eventId = document.getElementById('eventId').value;
        if (!eventId) {
            alert('Cannot delete a new event');
            return;
        }
    
        if (confirm('Are you sure you want to delete this event?')) {
            var formData = new FormData();
            formData.append('id', eventId);
            formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
    
            fetch('/delete_event/', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    var existingEvent = calendar.getEventById(eventId);
                    if (existingEvent) {
                        existingEvent.remove();
                    }
                    closeModal();
                } else {
                    alert('Error deleting event: ' + data.error);
                }
            })
            .catch(error => console.error('Error:', error));
        }
    }   
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    document.getElementById('eventAllDay').addEventListener('change', function() {
        updateDateTimeInputs(this.checked);
    });

    document.getElementById('deleteEventButton').addEventListener('click', deleteEvent);

    </script>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.30.1/moment.min.js"></script>
{% endblock %}
```

# --- File: cs_nea/templates/scheduling/create_lesson.html ---

```html
{% extends "_dashboard.html" %}

{% block content %}
<h2>Create a Lesson</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Create Lesson</button>
</form>
{% endblock %}
```

# --- File: cs_nea/templates/scheduling/student_schedule_lesson.html ---

```html
{% extends "_dashboard.html" %}
{% load widget_tweaks %}

{% block name %}Request a Lesson{% endblock %}

{% block content %}
<div class="bg-white rounded-lg shadow-md p-6 h-full">
    <div class="h-full flex flex-col overflow-hidden">
        <div class="flex-grow overflow-y-auto">
            <div class="container mx-auto p-4 h-full">
                <form id="lessonRequestForm" method="post">
                    {% csrf_token %}
                    
                    <div class="flex flex-col gap-4 justify-center w-full">
                        <!-- Teacher field -->
                        <div class="w-full">
                            {{ form.teacher.label_tag }}
                            {% render_field form.teacher class="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" %}
                            {% if form.teacher.errors %}
                                {% for error in form.teacher.errors %}
                                    <p class="text-red-500 text-xs italic">{{ error }}</p>
                                {% endfor %}
                            {% endif %}
                        </div>

                        <!-- Calendar container -->
                        <div id="calendar-container" class="w-full hidden mt-4">
                            <div id="calendar"></div>
                        </div>

                        <!-- Other form fields -->
                        {% for field in form %}
                            {% if field.name != 'teacher' %}
                            <div class="w-full">
                                {{ field.label_tag }}
                                {% render_field field class="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" %}
                                {% if field.errors %}
                                    {% for error in field.errors %}
                                        <p class="text-red-500 text-xs italic">{{ error }}</p>
                                    {% endfor %}
                                {% endif %}
                            </div>
                            {% endif %}
                        {% endfor %}

                        <input type="hidden" name="timezone">
                        
                        <div class="pt-6">
                            <button type="submit" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline">
                                Submit Lesson Request
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<!-- Modal -->
<div id="confirmModal" class="fixed inset-0 z-50 overflow-y-auto hidden bg-black bg-opacity-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-8 m-4 max-w-xl w-full">
            <h2 class="text-xl mb-4">Confirm Lesson Request</h2>
            <p class="mb-4">Are you sure you want to submit this lesson request?</p>
            <div class="flex justify-end space-x-2">
                <button id="cancelButton" class="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md">Cancel</button>
                <button id="confirmButton" class="px-4 py-2 bg-blue-500 text-white text-base font-medium rounded-md">Confirm</button>
            </div>
        </div>
    </div>
</div>


    
<script>
    // Adds timezone input to form
    document.addEventListener('DOMContentLoaded', function() {
        var timezoneInput = document.createElement('input');
        timezoneInput.setAttribute('type', 'hidden');
        timezoneInput.setAttribute('name', 'timezone');
        timezoneInput.setAttribute('value', Intl.DateTimeFormat().resolvedOptions().timeZone);
        document.getElementById('lessonRequestForm').appendChild(timezoneInput);
    });

    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('calendar');
        var calendarContainer = document.getElementById('calendar-container');
        var teacherSelect = document.getElementById('teacher-select');
        var form = document.getElementById('lessonRequestForm');
        var modal = document.getElementById('confirmModal');
        var cancelButton = document.getElementById('cancelButton');
        var confirmButton = document.getElementById('confirmButton');
    
        if (!teacherSelect) {
            console.error('Teacher select element not found');
            return;
        }
    
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            height: 'auto',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek'
            },
            events: [],
        });
    
        teacherSelect.addEventListener('change', function() {
            var teacherId = this.value;
            if (teacherId) {
                calendarContainer.classList.remove('hidden');
                if (!calendar.isRendered) {
                    calendar.render();
                    calendar.isRendered = true;
                }
                fetch(`/get_teacher_schedule/${teacherId}/`)
                    .then(response => response.json())
                    .then(data => {
                        calendar.removeAllEvents();
                        calendar.addEventSource(data);
                    })
                    .catch(error => console.error('Error:', error));
            } else {
                calendarContainer.classList.add('hidden');
                calendar.removeAllEvents();
            }
        });
    
        // Show modal on form submit
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            modal.classList.remove('hidden');
        });
    
        // Hide modal on cancel
        cancelButton.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    
        // Submit form on confirm
        confirmButton.addEventListener('click', function() {
            form.submit();
        });
    
        if (teacherSelect.value) {
            teacherSelect.dispatchEvent(new Event('change'));
        }
    });
</script>
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js'></script>
{% endblock %}
```

# --- File: cs_nea/templates/scheduling/reschedule_lesson.html ---

```html
{% extends "_dashboard.html" %}
{% load widget_tweaks %}
{% block name %}Request Lesson Rescheduling{% endblock %}
{% block content %}

<div class="container mx-auto" x-data="{ showModal: false }">
    <form method="post" class="flex flex-col bg-white rounded-lg shadow-md p-6 gap-4" @submit.prevent="showModal = true" x-ref="form">
        {% csrf_token %}
        {% for field in form %}
            <div class="justify-center w-full">
                <label class="block text-gray-700 text-sm font-bold" for="{{ field.id_for_label }}">
                    {{ field.label }}
                </label>
                {% render_field field class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" %}
                {% if field.errors %}
                    {% for error in field.errors %}
                        <p class="text-red-500 text-xs italic mt-1">{{ error }}</p>
                    {% endfor %}
                {% endif %}
            </div>
        {% endfor %}

        <div class="pt-6">
            <button type="submit" class="bg-purple-500 text-white font-semibold py-2 px-4 w-full rounded focus:outline-none focus:shadow-outline hover:bg-purple-600">
                Submit Rescheduling Request
            </button>
        </div>
    </form>

    <!-- Confirmation Modal -->
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full" x-show="showModal" x-cloak>
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3 text-center">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Confirm Rescheduling Request</h3>
                <div class="mt-2 px-7 py-3">
                    <p class="text-gray-500">Are you sure you want to submit this rescheduling request?</p>
                </div>
                <div class="items-center px-4 py-3">
                    <button @click="showModal = false" class="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md w-24 mr-2 hover:bg-gray-600">Cancel</button>
                    <button @click="$refs.form.submit()" class="px-4 py-2 bg-purple-500 text-white text-base font-medium rounded-md w-24 hover:bg-purple-600">Confirm</button>
                </div>
            </div>
        </div>
    </div>
</div>

{% endblock %}
```

# --- File: cs_nea/templates/scheduling/create_other_event.html ---

```html
{% extends "_dashboard.html" %}

{% endblock %}
{% block content %}
<h2>Create Other Event</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Create Event</button>
</form>
{% endblock %}
```

# --- File: cs_nea/templates/scheduling/teacher_schedule_lesson.html ---

```html
{% extends "_dashboard.html" %}
{% load widget_tweaks %}
{% block name %}Schedule or Request a Lesson{% endblock %}
{% block content %}

<div class="bg-white rounded-lg shadow-md p-6 h-full">
    <div class="h-full flex flex-col overflow-hidden">
        <div class="flex-grow overflow-y-auto">
            <div class="container mx-auto p-4 h-full">
                <form id="lessonRequestForm" method="post">
                    {% csrf_token %}

                    <div class="flex flex-col gap-4 justify-center w-full">
                        <div class="w-full">
                            {{ form.student.label_tag }}
                            {% render_field form.student class="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" id="student-select" %}
                            {% if form.student.errors %}
                                {% for error in form.student.errors %}
                                    <p class="text-red-500 text-xs italic">{{ error }}</p>
                                {% endfor %}
                            {% endif %}
                        </div>

                        <div id="calendar-container" class="w-full hidden mt-4">
                            <div id="calendar"></div>
                        </div>

                        {% for field in form %}
                            {% if field.name != 'student' %}
                                <div class="w-full">
                                    {{ field.label_tag }}
                                    {% render_field field class="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" %}
                                    {% if field.errors %}
                                        {% for error in field.errors %}
                                            <p class="text-red-500 text-xs italic">{{ error }}</p>
                                        {% endfor %}
                                    {% endif %}
                                </div>
                            {% endif %}
                        {% endfor %}
                        
                        <input type="hidden" name="timezone">

                        <div class="pt-6">
                            <button type="submit" class="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline">
                                Submit Lesson Request
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<div id="confirmModal" class="fixed inset-0 z-50 overflow-y-auto hidden bg-black bg-opacity-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-8 m-4 max-w-xl w-full">
            <h2 class="text-xl mb-4">Confirm Lesson Request</h2>
            <p>Are you sure you want to submit this lesson request?</p>
            <div class="flex justify-end space-x-2 mt-4">
                <button id="cancelButton" class="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
                    Cancel
                </button>
                <button id="confirmButton" class="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded">
                    Confirm
                </button>
            </div>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        var timezoneInput = document.createElement('input');
        timezoneInput.setAttribute('type', 'hidden');
        timezoneInput.setAttribute('name', 'timezone');
        timezoneInput.setAttribute('value', Intl.DateTimeFormat().resolvedOptions().timeZone);
        document.getElementById('lessonRequestForm').appendChild(timezoneInput);
    });
    
    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('calendar');
        var calendarContainer = document.getElementById('calendar-container');
        var studentSelect = document.getElementById('student-select');
        var form = document.getElementById('lessonRequestForm');
        var modal = document.getElementById('confirmModal');
        var cancelButton = document.getElementById('cancelButton');
        var confirmButton = document.getElementById('confirmButton');
    
        if (!studentSelect) {
            console.error('Student select element not found');
            return;
        }
    
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            height: 'auto',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek'
            },
            events: [],
        });
    
        studentSelect.addEventListener('change', function() {
            var studentId = this.value;
            if (studentId) {
                calendarContainer.classList.remove('hidden');
                if (!calendar.isRendered) {
                    calendar.render();
                    calendar.isRendered = true;
                }
                fetch(`/get_student_schedule/${studentId}/`)
                    .then(response => response.json())
                    .then(data => {
                        calendar.removeAllEvents();
                        calendar.addEventSource(data);
                    })
                    .catch(error => console.error('Error:', error));
            } else {
                calendarContainer.classList.add('hidden');
                calendar.removeAllEvents();
            }
        });
    
        // Show modal on form submit
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            modal.classList.remove('hidden');
        });
    
        // Hide modal on cancel
        cancelButton.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    
        // Submit form on confirm
        confirmButton.addEventListener('click', function() {
            form.submit();
        });
    
        if (studentSelect.value) {
            studentSelect.dispatchEvent(new Event('change'));
        }
    });
</script>
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js'></script>
{% endblock %}
```

# === Directory: cs_nea/templates/dashboard ===


# --- File: cs_nea/templates/dashboard/teacher_dashboard.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"></script>
{% endblock %}

{% block name %}
Teacher Dashboard
{% endblock %}

{% block content %}
<div class="flex h-full gap-4">
  <!-- Calendar Section -->
  <div class="w-1/2 pr-4">
      <div class="bg-white rounded-lg shadow-md p-6 h-full">
          <div id="calendar" class="h-full"></div>
      </div>
  </div>
  
  <!-- Attendance Table Section -->
  <div class="w-1/2 pl-4">
      <div class="bg-white rounded-lg shadow-md p-6 h-full overflow-y-auto">
          <h2 class="text-2xl font-semibold mb-4 text-neutral-800">Recent Lessons Attendance</h2>
          <table class="w-full">
              <thead>
                  <tr>
                      <th class="text-left text-neutral-800 font-semibold">Time</th>
                      <th class="text-left text-neutral-800 font-semibold">Student</th>
                      <th class="text-left text-neutral-800 font-semibold">Attendance</th>
                  </tr>
              </thead>
              <tbody id="attendanceTableBody">
                  <!-- Attendance rows will be populated here -->
              </tbody>
          </table>
      </div>
  </div>
</div>

<!-- TODO: I like this event modal popup thing, add this to other calendar implementations? -->
<!-- Event Modal -->
<div id="eventModal" class="fixed inset-0 z-50 overflow-y-auto hidden bg-black bg-opacity-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-8 m-4 max-w-xl w-full">
            <h2 id="modalTitle" class="text-xl mb-4"></h2>
            <form id="eventForm">
                {% csrf_token %}
                <input type="hidden" id="eventId" name="id">
                <div class="mb-4">
                    <label for="eventTitle" class="block text-sm font-medium text-gray-700">Event Title</label>
                    <input disabled type="text" id="eventTitle" name="title" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventStart" class="block text-sm font-medium text-gray-700">Start Time</label>
                    <input disabled type="datetime-local" id="eventStart" name="start" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventEnd" class="block text-sm font-medium text-gray-700">End Time</label>
                    <input disabled type="datetime-local" id="eventEnd" name="end" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="flex justify-end space-x-2">
                    <button type="button" onclick="closeModal()" class="px-4 py-2 bg-gray-300 text-black rounded hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50">Close</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Calendar functions and initalization
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridDay',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridDay'
        },
        height: '100%',
        events: '/get_calendar_data/',
        allDaySlot: false,
        timeZone: 'local',
        eventClick: function(info) {
            showEventDetails(info.event);
        }
    });
    calendar.render();

    // Function to fetch and update attendance table
    function updateAttendanceTable() {
      fetch('/get_recent_lessons/')
          .then(response => response.json())
          .then(data => {
              const tableBody = document.getElementById('attendanceTableBody');
              tableBody.innerHTML = '';
              data.forEach(lesson => {
                // Parse the UTC time and convert to local time
                const [datePart, timePart] = lesson.start_time.split(' ');
                const utcDate = new Date(datePart + 'T' + timePart + 'Z');
                const localTime = utcDate.toLocaleString(undefined, {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                });
                const row = `
                    <tr>
                        <td>${localTime}</td>
                        <td>${lesson.student_name}</td>
                        <td>
                            <input type="checkbox" 
                                   ${lesson.attendance ? 'checked' : ''} 
                                   onchange="updateAttendance(${lesson.lesson_id}, this.checked)">
                        </td>
                    </tr>
                `;
                tableBody.innerHTML += row;
              });
          });
  }

  // Initial load of attendance table
  updateAttendanceTable();

  // Refresh attendance table every 5 minutes
  setInterval(updateAttendanceTable, 300000);
});

// Form post to backend to update attendance
function updateAttendance(lessonId, attended) {
  fetch('/update_attendance/', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify({
          lesson_id: lessonId,
          attended: attended
      })
  })
  .then(response => response.json());
}

// TODO: JS code for event modal implementation, check TODO above.
function showEventDetails(event) {
    document.getElementById('modalTitle').textContent = 'Event Details';
    document.getElementById('eventId').value = event.id;
    document.getElementById('eventTitle').value = event.title;
    document.getElementById('eventStart').value = event.start.toISOString().slice(0, 16);
    document.getElementById('eventEnd').value = event.end.toISOString().slice(0, 16);
    document.getElementById('eventModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('eventModal').classList.add('hidden');
}
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.30.1/moment.min.js"></script>
{% endblock %}
```

# --- File: cs_nea/templates/dashboard/student_dashboard.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"></script>
{% endblock %}

{% block name %}
Student Dashboard
{% endblock %}

{% block content %}
<div class="bg-white rounded-lg shadow-md p-6 h-full">
    <div class="h-full flex flex-col overflow-hidden">
        <div class="flex-grow overflow-y-auto">
            <div class="container mx-auto p-4 h-full">
                <div class="bg-white shadow-md rounded-lg overflow-hidden h-full">
                    <div id="calendar" class="h-full"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- TODO: Nice event modal popup, add this to other calendar implementations? -->
<!-- Event Modal -->
<div id="eventModal" class="fixed inset-0 z-50 overflow-y-auto hidden bg-black bg-opacity-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-8 m-4 max-w-xl w-full">
            <h2 id="modalTitle" class="text-xl mb-4"></h2>
            <form id="eventForm">
                {% csrf_token %}
                <input type="hidden" id="eventId" name="id">
                <div class="mb-4">
                    <label for="eventTitle" class="block text-sm font-medium text-gray-700">Event Title</label>
                    <input disabled type="text" id="eventTitle" name="title" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventStart" class="block text-sm font-medium text-gray-700">Start Time</label>
                    <input disabled type="datetime-local" id="eventStart" name="start" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="mb-4">
                    <label for="eventEnd" class="block text-sm font-medium text-gray-700">End Time</label>
                    <input disabled type="datetime-local" id="eventEnd" name="end" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                </div>
                <div class="flex justify-end space-x-2">
                    <button type="button" onclick="closeModal()" class="px-4 py-2 bg-gray-300 text-black rounded hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50">Close</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridDay',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridDay'
        },
        height: '100%',
        events: '/get_calendar_data/',
        allDaySlot: false,
        eventClick: function(info) {
            showEventDetails(info.event);
        }
    });
    calendar.render();
});

// TODO: JS code for event modal implementation, check TODO above.
function showEventDetails(event) {
    document.getElementById('modalTitle').textContent = 'Event Details';
    document.getElementById('eventId').value = event.id;
    document.getElementById('eventTitle').value = event.title;
    document.getElementById('eventStart').value = event.start.toISOString().slice(0, 16);
    document.getElementById('eventEnd').value = event.end.toISOString().slice(0, 16);
    document.getElementById('eventModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('eventModal').classList.add('hidden');
}
</script>
{% endblock %}
```

# === Directory: cs_nea/templates/components ===


# --- File: cs_nea/templates/components/notification.html ---

```html
{% load static %}

<div id="notificationComponent" class="relative inline-block text-left mr-4">
    <button id="notificationButton" class="inline-flex items-center justify-center w-10 h-10 rounded-full bg-purple-500 text-white focus:outline-none relative">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
        </svg>
        <span id="notification-count" class="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-100 transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full" style="display: none;"></span>
    </button>

    <div id="notificationDropdown" class="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none" role="menu" aria-orientation="vertical" aria-labelledby="menu-button" tabindex="-1" style="display: none;">
        <div id="notificationList" class="py-1 max-h-80 overflow-y-auto" role="none">
            <!-- Notifications will be inserted here -->
        </div>
    </div>
</div>

<script>
// Listens for DOMContentLoaded event and initializes the notification component
document.addEventListener('DOMContentLoaded', function() {
    const notificationComponent = {
        button: document.getElementById('notificationButton'),
        dropdown: document.getElementById('notificationDropdown'),
        list: document.getElementById('notificationList'),
        countElement: document.getElementById('notification-count'),
        isOpen: false,
        notifications: [],
        unreadCount: 0,

        init: function() {
            this.button.addEventListener('click', () => this.toggleNotifications());
            document.addEventListener('click', (e) => this.handleOutsideClick(e));
            this.fetchNotifications();
        },

        toggleNotifications: function() {
            this.isOpen = !this.isOpen;
            this.dropdown.style.display = this.isOpen ? 'block' : 'none';
            if (this.isOpen) {
                this.fetchNotifications();
            }
        },

        handleOutsideClick: function(event) {
            if (this.isOpen && !this.dropdown.contains(event.target) && !this.button.contains(event.target)) {
                this.toggleNotifications();
            }
        },

        fetchNotifications: function() {
            fetch("/get_notifications/")
                .then(response => response.json())
                .then(data => {
                    this.notifications = data;
                    this.updateNotificationList();
                    this.updateUnreadCount();
                });
        },

        updateNotificationList: function() {
            this.list.innerHTML = '';
            if (this.notifications.length === 0) {
                this.list.innerHTML = '<div class="px-4 py-3 text-sm text-gray-700">No new notifications</div>';
            } else {
                this.notifications.forEach(notification => {
                    const notificationElement = this.createNotificationElement(notification);
                    this.list.appendChild(notificationElement);
                });
            }
        },
        // Creates a notification element if there are new notifications
        createNotificationElement: function(notification) {
            const div = document.createElement('div');
            div.className = 'flex items-center px-4 py-3 hover:bg-gray-100';
            div.innerHTML = `
                <div class="flex-grow">
                    <p class="text-sm text-gray-700">${notification.content}</p>
                    <p class="text-xs text-gray-500">${this.formatDateTime(notification.timestamp)}</p>
                </div>
                <button class="ml-2 text-gray-400 hover:text-gray-600" onclick="notificationComponent.dismissNotification(${notification.id})">
                    <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            `;
            return div;
        },
        // Dismisses and removes a notifcation
        dismissNotification: function(id) {
            fetch(`/mark_notification_read/${id}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": this.getCookie("csrftoken"),
                },
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === "success") {
                        this.notifications = this.notifications.filter(n => n.id !== id);
                        this.updateNotificationList();
                        this.updateUnreadCount();
                    }
                });
        },

        updateUnreadCount: function() {
            this.unreadCount = this.notifications.filter(n => !n.is_read).length;
            this.countElement.textContent = this.unreadCount;
            this.countElement.style.display = this.unreadCount > 0 ? 'inline-flex' : 'none';
        },

        // Function to convert UTC to local
        formatDateTime: function(timestamp) {
            if (!timestamp) return "No date available";
            try {
                // Assume the timestamp is in UTC and convert it to ISO
                if (timestamp.includes('T')) {
                    // ISO format from websocket
                    date = new Date(timestamp);
                } else {
                    // Database format
                    date = new Date(timestamp.replace(' ', 'T') + 'Z');
                }
                
                if (isNaN(date.getTime())) {
                    console.error("Invalid date:", timestamp);
                    return "Invalid Date";
                }
                
                const localTimestamp = date.toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true,
                });
                
                return localTimestamp;
            } catch (error) {
                console.error("Error formatting date:", error);
                return "Date error";
            }
        },
        // Gets a cookie value from the document ensures validity
        getCookie: function(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };

    notificationComponent.init();

    window.notificationComponent = notificationComponent;

    // WebSocket connection for real-time notifications
    const notificationSocket = new WebSocket(
        'ws://' + window.location.host + '/ws/notifications/'
    );

    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'new_notification') {
            notificationComponent.notifications.unshift(data.notification);
            notificationComponent.updateNotificationList();
            notificationComponent.updateUnreadCount();
            notificationComponent.toggleNotifications();
        }
    };
});
</script>
```

# --- File: cs_nea/templates/components/current_user.html ---

```html
{% load static %}
<!-- Component is used to display the current user's name and profile picture -->
<div x-data="{ open: false }" class="relative inline-block text-left mr-4">
    <div>
        <button
            @click="open = !open"
            type="button"
            class="inline-flex justify-center w-full rounded-md shadow-sm px-4 py-2 bg-purple-500 text-sm font-medium text-white hover:bg-purple-600 ring-purple-800"
            id="options-menu"
            aria-haspopup="true"
            x-bind:aria-expanded="open"
        >
            {{ user.first_name }} {{ user.last_name }}
            <svg
                class="-mr-1 ml-2 h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
            >
                <path
                    fill-rule="evenodd"
                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                    clip-rule="evenodd"
                />
            </svg>
        </button>
    </div>

    <div
        x-show="open"
        @click.away="open = false"
        class="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-neutral-100"
    >
        <div
            class="py-1"
            role="menu"
            aria-orientation="vertical"
            aria-labelledby="options-menu"
        >
            <a
                href="{% url 'settings' %}"
                class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                role="menuitem"
                >Settings</a
            >
            <a
                href="{% url 'user_profile' %}"
                class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                role="menuitem"
                >Profile</a
            >
            <a
                href="{% url 'logout' %}"
                class="block px-4 py-2 text-sm hover:bg-neutral-200 text-neutral-800"
                role="menuitem"
                >Log out</a
            >
        </div>
    </div>
</div>

```

# === Directory: cs_nea/templates/users ===


# --- File: cs_nea/templates/users/profile.html ---

```html
{% extends "_dashboard.html" %} 

{% block name %}Profile{% endblock %} 

{% block content %}
<div class="flex flex-col gap-4 justify-center w-full max-w-md">
    <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
            <div class="text-lg font-semibold">Name</div>
            <div>{{ user.first_name }} {{ user.last_name }}</div>
        </div>
        <div class="flex flex-col gap-2">
            <div class="text-lg font-semibold">Email</div>
            <div>{{ user.email }}</div>
        </div>
        <div class="flex flex-col gap-2">
            <div class="text-lg font-semibold">Contact Number</div>
            <div>{{ user.contact_number }}</div>
        </div>
    </div>
</div>
{% endblock content %}

```

# --- File: cs_nea/templates/users/account_recovery.html ---

```html
{% extends "_base.html" %}
{% load widget_tweaks %}

<!-- Account recovery page -->
{% block content %}
<div class="flex pt-28 justify-center" x-data="{ isLoading: false }">
  <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
    <div class="text-4xl font-semibold">Account Recovery</div>
    
    {% if messages %}
      {% for message in messages %}
        <div class="px-4 py-3 {% if message.tags == 'error' %}bg-red-100 border border-red-400 text-red-700{% else %}bg-green-100 border border-green-400 text-green-700{% endif %} rounded" role="alert">
          <span class="block sm:inline">{{ message }}</span>
        </div>
      {% endfor %}
    {% endif %}

    <form method="post" @submit="isLoading = true">
      {% csrf_token %}
      {% for field in form %}
        <div class="mb-4">
          <label class="block text-neutral-800 text-sm font-bold mb-2" for="{{ field.id_for_label }}">
            {{ field.label }}
          </label>
          {{ field|add_class:"shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" }}
          {% if field.errors %}
            {% for error in field.errors %}
              <p class="text-red-500 text-xs italic">{{ error }}</p>
            {% endfor %}
          {% endif %}
        </div>
      {% endfor %}
      <div class="flex items-center justify-between">
        <button class="bg-purple-500 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded focus:outline-none focus:shadow-outline" type="submit" :disabled="isLoading">
          <span x-show="!isLoading">Recover Account</span>
          <span x-show="isLoading" class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </span>
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock content %}
```

# --- File: cs_nea/templates/users/two_factor_verify.html ---

```html
{% extends "_base.html" %}
{% load widget_tweaks %}

{% block content %}
<!-- 2-FA verification page -->
<div class="flex pt-28 justify-center" x-data="{ isLoading: false }">
  <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
    <div class="text-4xl font-semibold">Two-Factor Authentication</div>
    
    {% if messages %}
      {% for message in messages %}
        <div class="px-4 py-3 {% if message.tags == 'error' %}bg-red-100 border border-red-400 text-red-700{% else %}bg-green-100 border border-green-400 text-green-700{% endif %} rounded" role="alert">
          <span class="block sm:inline">{{ message }}</span>
        </div>
      {% endfor %}
    {% endif %}

    <form method="post" @submit="isLoading = true">
      {% csrf_token %}
      {% for field in form %}
        <div class="mb-4">
          <label class="block text-neutral-800 text-sm font-bold mb-2" for="{{ field.id_for_label }}">
            {{ field.label }}
          </label>
          {{ field|add_class:"shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" }}
          {% if field.errors %}
            {% for error in field.errors %}
              <p class="text-red-500 text-xs italic">{{ error }}</p>
            {% endfor %}
          {% endif %}
        </div>
      {% endfor %}
      <div class="flex items-center justify-between">
        <button class="bg-purple-500 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded focus:outline-none focus:shadow-outline" type="submit" :disabled="isLoading">
          <span x-show="!isLoading">Verify</span>
          <span x-show="isLoading" class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </span>
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock content %}

```

# --- File: cs_nea/templates/users/password_reset.html ---

```html
{% extends "_base.html" %}
{% load widget_tweaks %}

{% block content %}
<div class="flex pt-28 justify-center" x-data="{ isLoading: false }">
  <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
    <div class="text-4xl font-semibold">Reset Your Password</div>
    
    {% if messages %}
      {% for message in messages %}
        <div class="px-4 py-3 {% if message.tags == 'error' %}bg-red-100 border border-red-400 text-red-700{% else %}bg-green-100 border border-green-400 text-green-700{% endif %} rounded" role="alert">
          <span class="block sm:inline">{{ message }}</span>
        </div>
      {% endfor %}
    {% endif %}
    
    <!-- Form for resetting password -->
    <form method="post" @submit="isLoading = true">
      {% csrf_token %}
      {% for field in form %}
        <div class="mb-4">
          <label class="block text-neutral-800 text-sm font-bold mb-2" for="{{ field.id_for_label }}">
            {{ field.label }}
          </label>
          {{ field|add_class:"shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" }}
          {% if field.errors %}
            {% for error in field.errors %}
              <p class="text-red-500 text-xs italic">{{ error }}</p>
            {% endfor %}
          {% endif %}
        </div>
      {% endfor %}
      <div class="flex items-center justify-between">
        <button class="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline" type="submit" :disabled="isLoading">
          <span x-show="!isLoading">Reset Password</span>
          <span x-show="isLoading" class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Resetting...
          </span>
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock content %}
```

# --- File: cs_nea/templates/users/login.html ---

```html
{% extends "_base.html" %} {% load widget_tweaks %} 

<!-- Login page -->
{% block content %}
<form class="flex pt-28 justify-center" method="post">
    {% csrf_token %}
    <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
        {% if request.path == "/student/login" %}
        <div class="text-4xl font-semibold">Student Log In</div>
        {% else %}
        <div class="text-4xl font-semibold">Teacher Log In</div>
        {% endif %} {% if form.non_field_errors %}
        <div
            class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
            role="alert"
        >
            {% for error in form.non_field_errors %}
            <p>{{ error }}</p>
            {% endfor %}
        </div>
        {% endif %} {% for field in form %}
        <div class="w-full">
            <label
                class="text-neutral-800 text-sm font-bold"
                for="{{ field.id_for_label }}"
            >
                {{ field.label }}
            </label>
            {{ field|add_class:"shadow border rounded w-full text-gray-700 focus:border-purple-500" }} 
            {% if field.errors %} {% for error in field.errors %}
            <p class="text-red-500 text-xs italic">{{ error }}</p>
            {% endfor %} {% endif %}
        </div>
        {% endfor %}
        <div>
            <a
                href="{% url 'account_recovery' %}"
                class="text-neutral-800 hover:underline text-sm font-semibold"
                >Forgot password?</a
            >
        </div>
        <div>
            <input
                class="bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800 w-full"
                type="submit"
                value="Log In"
            />
        </div>
    </div>
</form>
{% endblock content %} 


{% block navright %} 
<!-- Student specific login and signups -->
{% if 'student/login' in request.path %}
<a href="{% url 'student_login' %}">
    <button
        type="button"
        class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 ring-neutral-500"
    >
        Log in
    </button>
</a>
<a href="{% url 'student_signup' %}">
    <button
        type="button"
        class="bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
    >
        Sign up
    </button>
</a>
<!-- Teacher specific login and signups -->
{% elif 'teacher/login' in request.path %}
<a href="{% url 'teacher_login' %}">
    <button
        type="button"
        class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 ring-neutral-500"
    >
        Log in
    </button>
</a>
<a href="{% url 'teacher_signup' %}">
    <button
        type="button"
        class="bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
    >
        Sign up
    </button>
</a>
{% endif %} {% endblock navright %}

```

# --- File: cs_nea/templates/users/account_recovery_2fa.html ---

```html
{% extends "_base.html" %}
{% load widget_tweaks %}

<!-- Account recovery page for 2FA -->
{% block content %}
<div class="flex pt-28 justify-center" x-data="{ isLoading: false }">
  <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
    <div class="text-4xl font-semibold">Two-Factor Authentication</div>
    <p class="text-neutral-600">Please enter the 6-digit code sent to your email.</p>
    
    {% if messages %}
      {% for message in messages %}
        <div class="px-4 py-3 {% if message.tags == 'error' %}bg-red-100 border border-red-400 text-red-700{% else %}bg-green-100 border border-green-400 text-green-700{% endif %} rounded" role="alert">
          <span class="block sm:inline">{{ message }}</span>
        </div>
      {% endfor %}
    {% endif %}

    <form method="post" @submit="isLoading = true">
      {% csrf_token %}
      {% for field in form %}
        <div class="mb-4">
          <label class="block text-neutral-800 text-sm font-bold mb-2" for="{{ field.id_for_label }}">
            {{ field.label }}
          </label>
          {{ field|add_class:"shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" }}
          {% if field.errors %}
            {% for error in field.errors %}
              <p class="text-red-500 text-xs italic">{{ error }}</p>
            {% endfor %}
          {% endif %}
        </div>
      {% endfor %}
      <div class="flex items-center justify-between">
        <button class="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline" type="submit" :disabled="isLoading">
          <span x-show="!isLoading">Verify</span>
          <span x-show="isLoading" class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Verifying...
          </span>
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock content %}
```

# --- File: cs_nea/templates/users/settings.html ---

```html
<!-- users/templates/users/settings.html -->
{% extends "_dashboard.html" %}
{% load widget_tweaks %}

{% block name %}User Settings{% endblock %}

{% block content %}
<div class="container mx-auto">
    
    <!-- Iterates through messages and displays them -->
    {% if messages %}
    <div class="mb-4">
        {% for message in messages %}
        <div class="p-4 {% if message.tags == 'success' %}bg-green-100 text-green-700{% elif message.tags == 'error' %}bg-red-100 text-red-700{% else %}bg-blue-100 text-blue-700{% endif %} rounded">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <form method="post" class="space-y-4">
        {% csrf_token %}
        
        {% for field in form %}
        <div>
            <label for="{{ field.id_for_label }}" class="block text-sm font-medium text-gray-700">
                {{ field.label }}
            </label>
            <div class="mt-1">
                {% if field.name == 'two_factor_enabled' %}
                    {{ field|add_class:"h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" }}
                {% else %}
                    {{ field|add_class:"shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md" }}
                {% endif %}
            </div>
            {% if field.help_text %}
            <p class="mt-2 text-sm text-gray-500">{{ field.help_text }}</p>
            {% endif %}
            {% for error in field.errors %}
            <p class="mt-2 text-sm text-red-600">{{ error }}</p>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div>
            <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                Save Changes
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

# --- File: cs_nea/templates/users/signup.html ---

```html
{% extends "_base.html" %} {% load widget_tweaks %} {% block content %}

{% if request.path == "/student/signup" %}
  <form class="flex pt-28 justify-center" method="post">
    {% csrf_token %}
    <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
      <div class="text-4xl font-semibold">Student Sign Up</div>

      {% if form.non_field_errors %}
        <div class="flex bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded" role="alert">
          {% for error in form.non_field_errors %}
            <p>{{ error }}</p>
          {% endfor %}
        </div>
        {% endif %}

      {% for field in form %}
        <div class="w-full">
        <label class="text-neutral-800 text-sm font-bold" for="{{ field.id_for_label }}">
        {{ field.label }}
        </label>
        {% if field.name == 'contact_number' %}
          <div class="flex gap-2">
            {{ field|add_class:"w-full" }}
          </div>
        {% else %}
          {{ field|add_class:"shadow border rounded w-full text-gray-700 focus:border-purple-500" }}
        {% endif %}
        {% if field.errors %}
          {% for error in field.errors %}
            <p class="text-red-500 text-xs italic">{{ error }}</p>
          {% endfor %}
        {% endif %}
        </div>
      {% endfor %}

      <div>
        <input
          class="w-full bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
          type="submit"
          value="Sign Up"
        />
      </div>
    </div>
  </form>
{% elif request.path == "/teacher/signup" %}
  <form class="flex pt-28 justify-center" method="post">
    {% csrf_token %}
    <div class="flex flex-col gap-4 justify-center w-full max-w-md px-4">
      <div class="text-4xl font-semibold">Teacher Sign Up</div>
      
      {% if messages %}
        {% for message in messages %}
          <div class="px-4 py-3 {% if message.tags == 'error' %}bg-red-100 border border-red-400 text-red-700{% else %}bg-green-100 border border-green-400 text-green-700{% endif %} rounded" role="alert">
            {{ message }}
          </div>
        {% endfor %}
      {% endif %}

      {% if form.non_field_errors %}
        <div class="flex bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded" role="alert">
          {% for error in form.non_field_errors %}
            <p>{{ error }}</p>
          {% endfor %}
        </div>
        {% endif %}

      {% for field in form %}
        <div class="w-full">
        <label class="text-neutral-800 text-sm font-bold" for="{{ field.id_for_label }}">
        {{ field.label }}
        </label>
        {% if field.name == 'contact_number' %}
          <div class="flex gap-2">
            {{ field|add_class:"w-full" }}
          </div>
        {% else %}
          {{ field|add_class:"shadow border rounded w-full text-gray-700 focus:border-purple-500" }}
        {% endif %}
        {% if field.errors %}
          {% for error in field.errors %}
            <p class="text-red-500 text-xs italic">{{ error }}</p>
          {% endfor %}
        {% endif %}
        </div>
      {% endfor %}

      <div>
        <input
          class="w-full bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
          type="submit"
          value="Sign Up"
        />
      </div>
    </div>
  </form>
{% endif %}

{% endblock content %} 

<!-- Navbar links -->
{% block navright %}
  {% if request.path == "/student/signup" %}
    <a href="{% url 'student_login' %}">
      <button
        type="button"
        class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 ring-neutral-500"
      >
        Log in
      </button>
    </a>
    <a href="{% url 'student_signup' %}">
      <button
        type="button"
        class="bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
      >
        Sign up
      </button>
    </a>
    {% endif %}
  {% if request.path == "/teacher/signup" %}
    <a href="{% url 'teacher_login' %}">
      <button
        type="button"
        class="bg-neutral-700 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-neutral-800 hover:ring-2 ring-neutral-500"
      >
        Log in
      </button>
    </a>
    <a href="{% url 'teacher_signup' %}">
      <button
        type="button"
        class="bg-purple-500 text-white font-medium rounded-lg px-5 py-2.5 hover:bg-purple-600 hover:ring-2 ring-purple-800"
      >
        Sign up
      </button>
    </a>
  {% endif %}
{% endblock navright %}

```

# === Directory: cs_nea/templates/users/student_templates ===


# --- File: cs_nea/templates/users/student_templates/student_invites.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}
{% block name %}Pending Invites{% endblock %}
{% block content %}

<!-- Student view for pending invites -->
<div class="container mx-auto">
    {% if invites %}
    <div class="space-y-6">
        {% for invite in invites %}
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center">
                <div class="mb-4 md:mb-0">
                    <h3 class="text-xl font-semibold text-gray-800">
                        {% if invite.teacher.user %}
                            {{ invite.teacher.user.get_full_name }}
                        {% else %}
                            Unknown Teacher
                        {% endif %}
                    </h3>
                    <p class="text-gray-600">{{ invite.teacher.user.email }}</p>
                </div>
                <a href="{% url 'accept_invite' invite.id %}" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition duration-300">
                    Accept Invite
                </a>
            </div>
            {% if invite.message %}
            <div class="mt-4 p-4 bg-gray-100 rounded-md">
                <h4 class="font-semibold mb-2">Message:</h4>
                <p class="text-gray-700">{{ invite.message }}</p>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-lg text-gray-600">No pending invites.</p>
    {% endif %}
</div>

{% endblock %}
```

# --- File: cs_nea/templates/users/student_templates/student_teachers.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}
{% block name %}Teachers{% endblock %}
{% block content %}

<!-- Student view for all connected teachers -->
<div class="container mx-auto">
    {% if teachers %}
    <div class="grid grid-cols-1 gap-6">
        {% for teacher in teachers %}
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex flex-col lg:flex-row">
                <div class="w-full lg:w-1/2 pr-0 lg:pr-4">
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">{{ teacher.user.get_full_name }}</h3>
                    <p class="mb-1"><span class="font-semibold">Email:</span> {{ teacher.user.email }}</p>
                    <p class="mb-1"><span class="font-semibold">Phone Number:</span> {{ teacher.user.contact_number }}</p>
                </div>
                <div class="w-full lg:w-1/2 mt-4 lg:mt-0 lg:border-l lg:border-gray-200 lg:pl-4">
                    <h4 class="font-semibold mb-2">Extra Information:</h4>
                    <p class="text-gray-600">{{ teacher.extra_teacher_info|default:"No additional information provided." }}</p>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-lg text-gray-600">You don't have any teachers yet.</p>
    {% endif %}
</div>

{% endblock %}
```

# === Directory: cs_nea/templates/users/teacher_templates ===


# --- File: cs_nea/templates/users/teacher_templates/teacher_students.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block name %}My Students{% endblock %}

<!-- Teacher view for all students and notes functionaility -->
{% block content %}
<div class="container mx-auto">
    {% if students %}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {% for student in students %}
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex flex-col lg:flex-row">
                <div class="w-full lg:w-1/2 pr-0 lg:pr-4">
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">{{ student.user.get_full_name }}</h3>
                    <p>Email: {{ student.user.email }}</p>
                    <p>Phone Number: {{ student.user.contact_number }}</p>
                    <p>Grade: {{ student.grade_level }}</p>
                    <p>Extra Information: {{ student.extra_student_info }}</p>
                    <button onclick="toggleNotes('notes-{{ student.student_id }}')" class="mt-2 bg-green-500 text-white px-4 py-2 rounded">Toggle Notes</button>
                </div>

                <div class="w-full lg:w-1/2 mt-4 lg:mt-0">
                    <div id="notes-{{ student.student_id }}" class="hidden bg-yellow-100 p-4 rounded-md">
                        <h4 class="font-semibold mb-2">Notes:</h4>
                        {% for note in notes %}
                            {% if note.student == student %}
                            <div class="mb-2 p-2 bg-white rounded">
                                <p>{{ note.note_content }}</p>
                                <p class="text-sm text-gray-500">Created: {{ note.created_at|date:"F d, Y, h:i a" }}</p>
                                <div class="mt-2">
                                    <button onclick="showEditForm('{{ note.note_id }}')" class="text-blue-500">Edit</button>
                                    <form method="post" class="inline">
                                        {% csrf_token %}
                                        <input type="hidden" name="action" value="delete_note">
                                        <input type="hidden" name="note_id" value="{{ note.note_id }}">
                                        <button type="submit" class="text-red-500 ml-2">Delete</button>
                                    </form>
                                </div>
                                <div id="edit-form-{{ note.note_id }}" class="hidden mt-2">
                                    <form method="post">
                                        {% csrf_token %}
                                        <input type="hidden" name="action" value="edit_note">
                                        <input type="hidden" name="note_id" value="{{ note.note_id }}">
                                        <textarea name="note_content" class="w-full p-2 border rounded">{{ note.note_content }}</textarea>
                                        <button type="submit" class="mt-2 bg-blue-500 text-white px-4 py-2 rounded">Update Note</button>
                                    </form>
                                </div>
                            </div>
                            {% endif %}
                        {% endfor %}
                        <form method="post" class="mt-4">
                            {% csrf_token %}
                            <input type="hidden" name="action" value="add_note">
                            <input type="hidden" name="student_id" value="{{ student.student_id }}">
                            {{ form.note_content }}
                            <button type="submit" class="mt-2 bg-green-500 text-white px-4 py-2 rounded">Add Note</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p>You don't have any students yet.</p>
    {% endif %}

    <div class="mt-8">
        <a href="{% url 'invite_student' %}" class="bg-purple-500 text-white px-6 py-3 rounded-lg hover:bg-purple-600 transition duration-300">Invite New Student</a>
    </div>
</div>

<script>
function toggleExtraInfo(id) {
    var element = document.getElementById(id);
    element.classList.toggle('hidden');
}

function toggleNotes(id) {
    var element = document.getElementById(id);
    element.classList.toggle('hidden');
}

function showEditForm(noteId) {
    var editForm = document.getElementById('edit-form-' + noteId);
    editForm.classList.toggle('hidden');
}
</script>
{% endblock %}
```

# --- File: cs_nea/templates/users/teacher_templates/invite_student.html ---

```html
{% extends "_dashboard.html" %}
{% load widget_tweaks %}

{% block name %}Invite Student{% endblock %}

<!-- Teacher view for inviting a student -->
{% block content %}
<div class="container mx-auto">
    <form method="post">
        {% csrf_token %}

        {% if form.non_field_errors %}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded" role="alert">
                {% for error in form.non_field_errors %}
                    <p>{{ error }}</p>
                {% endfor %}
            </div>
        {% endif %}

        {% for field in form %}
            <div class="w-full">
                <label class="block text-gray-700 text-sm font-bold mb-2" for="{{ field.id_for_label }}">
                    {{ field.label }}
                </label>
                {{ field|add_class:"shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline focus:border-purple-500" }}
                {% if field.errors %}
                    {% for error in field.errors %}
                        <p class="text-red-500 text-xs italic mt-1">{{ error }}</p>
                    {% endfor %}
                {% endif %}
            </div>
        {% endfor %}

        <div class="mt-6">
            <button
                type="submit"
                class="bg-purple-500 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline hover:bg-purple-600 transition duration-300"
            >
                Send Invite
            </button>
        </div>
    </form>
</div>
{% endblock content %}
```

# === Directory: cs_nea/templates/communications ===


# --- File: cs_nea/templates/communications/create_assignment.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}
{% load widget_tweaks %}

{% block name %}Create New Assignment{% endblock %}

{% block content %}
<div class="container mx-auto">
    <form method="post" class="bg-white shadow-md rounded-lg p-6">
        {% csrf_token %}
        <div class="mb-4">
            <label for="{{ form.student.id_for_label }}" class="block text-gray-700 text-sm font-bold mb-2">Student</label>
            {% render_field form.student class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" %}
        </div>
        <div class="mb-4">
            <label for="{{ form.task_content.id_for_label }}" class="block text-gray-700 text-sm font-bold mb-2">Task Content</label>
            {% render_field form.task_content class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" rows="4" %}
        </div>
        <div class="mb-6">
            <label for="{{ form.due_date.id_for_label }}" class="block text-gray-700 text-sm font-bold mb-2">Due Date</label>
            {% render_field form.due_date class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" %}
        </div>
        <div class="flex items-center justify-between">
            <button type="submit" class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition duration-300 ease-in-out">
                Create Task
            </button>
            <a href="{% url 'assignment_list' %}" class="inline-block align-baseline font-bold text-sm text-purple-500 hover:text-purple-800">
                Cancel
            </a>
        </div>
    </form>
</div>
{% endblock %}
```

# --- File: cs_nea/templates/communications/assignment_detail.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block name %}Assignment Details{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">    
    <div class="bg-white shadow-md rounded-lg p-6">
        <h3 class="text-2xl font-semibold text-gray-800 mb-4">{{ assignment.task_content }}</h3>
        <p class="text-gray-600 mb-2">Assigned by: {{ assignment.teacher.user.get_full_name }}</p>
        <p class="text-gray-600 mb-2">Assigned to: {{ assignment.student.user.get_full_name }}</p>
        <p class="text-gray-600 mb-2">Due: {{ assignment.due_date|date:"F d, Y H:i" }}</p>
        <p class="text-gray-600 mb-4">Status: 
            <!-- Checks if the assignment is completed -->
            <span class="{% if assignment.is_completed %}text-green-500{% else %}text-yellow-500{% endif %}">
                {% if assignment.is_completed %}Completed{% else %}Pending{% endif %}
            </span>
        </p>
        
        <!-- Validates user type and only shows the button if the user is a student -->
        {% if user.user_type == 1 and not assignment.is_completed %}
        <form method="post" action="{% url 'mark_completed' assignment.assignment_id %}">
            {% csrf_token %}
            <button type="submit" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out">
                Mark as Completed
            </button>
        </form>
        {% endif %}
        
        <a href="{% url 'assignment_list' %}" class="mt-4 inline-block bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded transition duration-300 ease-in-out">
            Back to Assignments
        </a>
    </div>
</div>
{% endblock %}
```

# --- File: cs_nea/templates/communications/message_list.html ---

```html
{% extends "_dashboard.html" %}

{% block name %} Direct Messages {% endblock %}

{% block content %}
<!-- Direct message list -->
<div class="container mx-auto bg-white rounded-lg shadow-md p-6">
    <ul class="space-y-2">
        {% for user in users %}
            <li>
                <a href="{% url 'direct_message' user.id %}" class="text-purple-800">
                    {{ user.get_full_name }}
                </a>
            </li>
        {% empty %}
            <li>No users available to message.</li>
        {% endfor %}
    </ul>
</div>
{% endblock %}
```

# --- File: cs_nea/templates/communications/direct_message.html ---

```html
{% extends "_dashboard.html" %}
{% block name %}Chat with {{ other_user.get_full_name }}{% endblock %}
{% block content %}

<div class="flex flex-col h-full">
    <div id="chat-messages" class="flex-1 overflow-y-auto border rounded-lg p-4 space-y-4">
        <!-- Messages will be displayed here dynamically -->
    </div>

    <div class="flex pb-6 pt-2">
        <input type="text" id="chat-message-input" class="flex-grow border rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Type your message...">
        <button id="chat-message-submit" class="bg-blue-500 text-white px-4 py-2 rounded-r-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500">Send</button>
    </div>
</div>

<script>
    // WebSocket connection to the server
    const chatSocket = new WebSocket(
        'ws://' + window.location.host + '/ws/dm/{{ other_user.id }}/'
    );

    const messageInput = document.querySelector('#chat-message-input');
    const messageSubmit = document.querySelector('#chat-message-submit');
    const chatMessages = document.querySelector('#chat-messages');

    let isConnected = false;
    let messageQueue = [];

    chatSocket.onopen = function(e) {
        isConnected = true;
        console.log("WebSocket connection established");
        sendQueuedMessages();
    };

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.error) {
            showError(data.error);
        } else {
            addMessageToChat(data.sender, data.message, data.timestamp);
        }
    };

    chatSocket.onclose = function(e) {
        isConnected = false;
        console.error("WebSocket connection closed unexpectedly");
        showError("Connection lost. Please refresh the page.");
    };

    messageSubmit.onclick = sendMessage;

    messageInput.onkeyup = function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    // Function to send a message
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            if (message.length > 1000) {
                showError("Message is too long. Please limit to 1000 characters.");
                return;
            }
            if (isConnected) {
                chatSocket.send(JSON.stringify({ 'message': message }));
            } else {
                messageQueue.push(message);
                showError("Connection lost. Message will be sent when reconnected.");
            }
            messageInput.value = '';
        } else {
            showError("Please enter a message before sending.");
        }
    }

    // Function to send queued messages in case of disconnect
    function sendQueuedMessages() {
        while (messageQueue.length > 0) {
            const message = messageQueue.shift();
            chatSocket.send(JSON.stringify({ 'message': message }));
        }
    }

    // Function to add a message to the chat
    function addMessageToChat(sender, message, timestamp) {
        const messageElement = document.createElement('div');
        const isCurrentUser = sender === "{{ user.get_full_name }}";
        
        messageElement.className = isCurrentUser ? 'flex flex-col items-end' : 'flex flex-col items-start';
        
        const dateTime = new Date(timestamp).toLocaleString();
        
        messageElement.innerHTML = `
            <div class="text-xs text-gray-500 mb-1">${sender} • ${dateTime}</div>
            <div class="bg-white rounded-lg p-3 shadow max-w-xs lg:max-w-md">
                <div class="text-sm">${escapeHTML(message)}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to show an error message
    function showError(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4';
        errorElement.role = 'alert';
        errorElement.innerHTML = `
            <strong class="font-bold">Error:</strong>
            <span class="block sm:inline">${message}</span>
        `;
        chatMessages.appendChild(errorElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        setTimeout(() => {
            errorElement.remove();
        }, 5000);
    }   

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }
</script>

{% endblock %}
```

# --- File: cs_nea/templates/communications/assignment_list.html ---

```html
{% extends "_dashboard.html" %}
{% load static %}

{% block name %}Assignments{% endblock %}

{% block content %}
<div class="container mx-auto">
    {% if user.user_type == 2 %}
    <a href="{% url 'create_assignment' %}" class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded mb-6 inline-block transition duration-300 ease-in-out">
        Create New Assignment
    </a>
    {% endif %}
    
    <ul class="space-y-4">
        <!-- Django template tags to iterate and display each assignment individually -->
        {% for assignment in assignments %}
        <li class="bg-white shadow-md rounded-lg p-6 transition duration-300 ease-in-out hover:shadow-lg">
            <h3 class="text-xl font-semibold text-gray-800 mb-2">{{ assignment.task_content }}</h3>
            <p class="text-gray-600 mb-2">Due: {{ assignment.due_date|date:"F d, Y H:i" }}</p>
            <p class="text-gray-600 mb-4">Status: 
                <span class="{% if assignment.is_completed %}text-green-500{% else %}text-yellow-500{% endif %}">
                    {% if assignment.is_completed %}Completed{% else %}Pending{% endif %}
                </span>
            </p>
            {% if user.user_type == 1 and not assignment.is_completed %}
            <form method="post" action="{% url 'mark_completed' assignment.assignment_id %}">
                {% csrf_token %}
                <button type="submit" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out">
                    Mark as Completed
                </button>
            </form>
            {% endif %}
        </li>
        {% empty %}
        <li class="text-gray-600">No tasks available.</li>
        {% endfor %}
    </ul>
</div>
{% endblock %}
```

# === Directory: cs_nea/communications ===


# --- File: cs_nea/communications/signals.py ---

```python
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

# Saves a notification config when user modifies it
@receiver(post_save, sender=User)
def save_notification_config(sender, instance, **kwargs):
    instance.notificationconfig.save()
```

# --- File: cs_nea/communications/tasks.py ---

```python
from django.utils import timezone
from .models import Notification, NotificationConfig
from scheduling.models import Lesson
from datetime import timedelta
# Celery is a task queue that allows you to run tasks asynchronously
from celery import shared_task

def send_notification(user, content):
    Notification.objects.create(receiver=user, content=content)
    # TODO: Implement other options of sending notifications

def schedule_notifications():
    # Timezone awareness
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
```

# --- File: cs_nea/communications/models.py ---

```python
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

```

# --- File: cs_nea/communications/consumers.py ---

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from .models import Message, MessageConfig

User = get_user_model()


# Direct message consumer - used for chatting with other users
class DirectMessageConsumer(AsyncWebsocketConsumer):
    # Gets the user ID from the URL route
    async def connect(self):
        self.user = self.scope["user"]
        self.other_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.room_name = f"dm_{min(self.user.id, int(self.other_user_id))}_{max(self.user.id, int(self.other_user_id))}"
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        previous_messages = await self.get_previous_messages()
        for message in previous_messages:
            message_data = await self.get_message_data(message)
            await self.send(text_data=json.dumps(message_data))

    # Disconnects the user from the room
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Function to recieve messages from other user
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        if await self.can_send_message():
            await self.save_message(message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": self.user.get_full_name(),
                    "timestamp": timezone.now().isoformat(),
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # Function to save a message for future display
    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(id=self.other_user_id)
        Message.objects.create(sender=self.user, receiver=other_user, content=content)

    # Function to get the previous messages saved for the user
    @database_sync_to_async
    def get_previous_messages(self):
        other_user = User.objects.get(id=self.other_user_id)
        return list(
            Message.objects.filter(
                (models.Q(sender=self.user) & models.Q(receiver=other_user))
                | (models.Q(sender=other_user) & models.Q(receiver=self.user))
            ).order_by("-timestamp")[:50][::-1]
        )

    @database_sync_to_async
    def get_message_data(self, message):
        return {
            "message": message.content,
            "sender": message.sender.get_full_name(),
            "timestamp": message.timestamp.isoformat(),
        }
        
    
    @database_sync_to_async
    def can_send_message(self):
        other_user = User.objects.get(id=self.other_user_id)
        # Check if the user has a message config for the other user through the message_config table
        config = MessageConfig.objects.filter(
            (models.Q(student=self.user) & models.Q(teacher=other_user))
            | (models.Q(student=other_user) & models.Q(teacher=self.user))
        ).first()
        return not config or not config.read_only

    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(id=self.other_user_id)
        return Message.objects.create(
            sender=self.user, receiver=other_user, content=content
        )

    # Receives messages from the other user in real-time
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        if await self.can_send_message():
            saved_message = await self.save_message(message)
            message_data = await self.get_message_data(saved_message)
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", **message_data}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))


# Notification consumer - used for receiving and sending notifications in real-time
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.notification_group_name = f"user_{self.user.id}_notifications"

        await self.channel_layer.group_add(
            self.notification_group_name, self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_group_name, self.channel_name
        )

    async def notification(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "new_notification", "notification": event["notification"]}
            )
        )

```

# --- File: cs_nea/communications/__init__.py ---

```python

```

# --- File: cs_nea/communications/apps.py ---

```python
from django.apps import AppConfig

# Communications app config
class CommunicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communications"
    def ready(self):
        import communications.signals
```

# --- File: cs_nea/communications/forms.py ---

```python
from django import forms
from .models import Assignment, NotificationConfig
from users.models import Student

# Assignment form for creating and editing assignments
class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["student", "task_content", "due_date"]
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop("teacher", None)
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields["student"].queryset = Student.objects.filter(
                invites__teacher=self.teacher, invites__status="accepted"
            )

# Notification config form for creating and editing notification configs
class NotificationConfigForm(forms.ModelForm):
    class Meta:
        model = NotificationConfig
        fields = [
            "receive_notification",
            "lesson_reminder",
            "assignment_notification",
            "message_notification",
            "attendance_notification",
            "t2r_requests",
            "cancellation_notification",
            "weekly_summary",
            "lesson_reminder_1hr",
            "lesson_reminder_24hr",
            "lesson_reminder_30min",
        ]

```

# --- File: cs_nea/communications/routing.py ---

```python
from django.urls import re_path
from . import consumers

# Websocket routing for real-time messaging and notifications
websocket_urlpatterns = [
    # Real time messaging routing
    re_path(r"ws/dm/(?P<user_id>\w+)/$", consumers.DirectMessageConsumer.as_asgi()),

    # Notification routing
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]


```

# --- File: cs_nea/communications/urls.py ---

```python
from django.urls import path
from . import views

urlpatterns = [
    # Notification URLs
    path("get_notifications/", views.get_notifications, name="get_notifications"),
    path(
        "mark_notification_read/<int:notification_id>/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    # Messaging URLs
    path("messages/", views.message_list, name="message_list"),
    path("messages/<int:user_id>/", views.direct_message, name="direct_message"),
    # Assignment URLs
    path("assignments/", views.assignment_list, name="assignment_list"),
    path("assignments/create/", views.create_assignment, name="create_assignment"),
    path(
        "assignments/<int:assignment_id>/",
        views.assignment_detail,
        name="assignment_detail",
    ),
    path(
        "assignments/<int:assignment_id>/complete/",
        views.mark_completed,
        name="mark_completed",
    ), 
]

```

# --- File: cs_nea/communications/views.py ---

```python
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Notification, Assignment, Note, NotificationConfig
from django.contrib.auth import get_user_model
from .forms import AssignmentForm, NotificationConfigForm
from django.utils import timezone
from users.models import Student, Teacher

User = get_user_model()

# Notification views - only JSON responses
@login_required
def notification_preferences(request):
    try:
        preferences = NotificationConfig.objects.get(user=request.user)
    except NotificationConfig.DoesNotExist:
        preferences = NotificationConfig(user=request.user)

    if request.method == 'POST':
        form = NotificationConfigForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            return redirect('notification_preferences')
    else:
        form = NotificationConfigForm(instance=preferences)

    return render(request, 'notification_preferences.html', {'form': form})

# Fetches notifications for the user
@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(
        receiver=request.user, is_read=False
    ).order_by("-timestamp")[:20]
    data = [
        {
            "id": notif.id,
            "content": notif.content,
            "timestamp": notif.timestamp.strftime("%Y-%m-%d %H:%M"),
        }
        for notif in notifications
    ]
    return JsonResponse(data, safe=False)

# Marks a notification as read
@require_POST
@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(
            id=notification_id, receiver=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({"status": "success"})
    except Notification.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Notification not found"}, status=404
        )


# Real time messaging view
@login_required
def message_list(request):
    if request.user.user_type == 1:  # Student
        student = Student.objects.get(user=request.user)
        connected_teachers = User.objects.filter(
            teacher__sent_invites__student=student,
            teacher__sent_invites__status='accepted',
            user_type=2
        ).distinct()
        users = connected_teachers
    else:  # Teacher
        teacher = Teacher.objects.get(user=request.user)
        connected_students = User.objects.filter(
            student__invites__teacher=teacher,
            student__invites__status='accepted',
            user_type=1
        ).distinct()
        users = connected_students

    return render(request, "communications/message_list.html", {"users": users})


@login_required
def direct_message(request, user_id):
    other_user = User.objects.get(id=user_id)
    return render(
        request, "communications/direct_message.html", {"other_user": other_user}
    )


# Assignments views
@login_required
@user_passes_test(lambda u: u.user_type == 2)
def create_assignment(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST, teacher=request.user.teacher)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = request.user.teacher
            assignment.save()
            messages.success(request, "Task created successfully.")
            return redirect("assignment_list")
    else:
        form = AssignmentForm(teacher=request.user.teacher)
    return render(request, "communications/create_assignment.html", {"form": form})


@login_required
def assignment_list(request):
    if request.user.user_type == 1:  # Student
        assignments = Assignment.objects.filter(student=request.user.student)
    else:  # Teacher
        assignments = Assignment.objects.filter(teacher=request.user.teacher)
    return render(
        request, "communications/assignment_list.html", {"assignments": assignments}
    )


@login_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    if request.user.user_type == 1 and assignment.student != request.user.student:
        messages.error(request, "You do not have permission to view this task.")
        return redirect("assignment_list")
    if request.user.user_type == 2 and assignment.teacher != request.user.teacher:
        messages.error(request, "You do not have permission to view this task.")
        return redirect("assignment_list")
    return render(
        request, "communications/assignment_detail.html", {"assignment": assignment}
    )

# Marks an assignment as completed
@login_required
@user_passes_test(lambda u: u.user_type == 1) # Checks user type
def mark_completed(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    if assignment.student != request.user.student:
        messages.error(request, "You do not have permission to mark this task.")
        return redirect("assignment_list")

    assignment.is_completed = True
    assignment.completion_date = timezone.now()
    assignment.save()

    messages.success(request, "Task marked as completed.")
    return redirect("assignment_list")
```
