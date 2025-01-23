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
from pytz import timezone as pytz_timezone, UnknownTimeZoneError
from django.utils.timezone import localtime
from django.urls import reverse

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
        user=teacher.user,
        start_datetime__gte=start,
        end_datetime__lte=end,
    )

    events = []
    for lesson in lessons:
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": "Busy",
            "start": lesson.start_datetime.isoformat(),
            "end": lesson.end_datetime.isoformat(),
            "color": "#383434", # Matched colour with tailwind colours
        })

    for event in calendar_events:
        events.append({
            "id": f"event_{event.event_id}",
            "title": "Busy",
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "#383434",
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
    calendar_events = CalendarEvent.objects.filter(
        user=student.user,
        start_datetime__gte=start,
        end_datetime__lte=end,
    )

    events = []
    for lesson in lessons:
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": "Busy",
            "start": lesson.start_datetime.isoformat(),
            "end": lesson.end_datetime.isoformat(),
            "color": "#383434", # Matched colour with tailwind colours
        })

    for event in calendar_events:
        events.append({
            "id": f"event_{event.event_id}",
            "title": "Busy",
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "#383434",
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
    # Convert to user's local timezone
    def localize_request(requests):
        for req in requests:
            if hasattr(req, "requested_datetime") and req.requested_datetime:
                req.requested_datetime_local = localtime(req.requested_datetime)
            if hasattr(req, "end_datetime") and req.end_datetime:
                req.end_datetime_local = localtime(req.end_datetime)
            if hasattr(req, "original_lesson") and hasattr(req.original_lesson, "start_datetime"):
                req.original_lesson.start_datetime_local = localtime(req.original_lesson.start_datetime)
        return requests

    # Filter requests based on user type
    if request.user.user_type == 1:
        scheduling_requests = LessonRequest.objects.filter(
            student=request.user.student, is_approved=False, is_sent_by_teacher=True
        )
        rescheduling_requests = ReschedulingRequest.objects.filter(
            original_lesson__student=request.user.student, is_approved=False
        )
    else:
        scheduling_requests = LessonRequest.objects.filter(
            teacher=request.user.teacher, is_approved=False, is_sent_by_teacher=False
        )
        rescheduling_requests = ReschedulingRequest.objects.filter(
            original_lesson__teacher=request.user.teacher, is_approved=False
        )

    # Localize datetimes
    scheduling_requests = localize_request(scheduling_requests)
    rescheduling_requests = localize_request(rescheduling_requests)

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
        form = RescheduleLessonForm(data=request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    rescheduling_request = form.save(commit=False)
                    rescheduling_request.requested_by = request.user
                    rescheduling_request.original_lesson = form.cleaned_data["lesson"]
                    rescheduling_request.requested_datetime = form.cleaned_data['requested_datetime']
                    rescheduling_request.end_datetime = form.cleaned_data['end_datetime']
                    rescheduling_request.save()
                    
                    # Create notification for the other party
                    other_user = (
                        rescheduling_request.original_lesson.teacher.user
                        if request.user.user_type == 1
                        else rescheduling_request.original_lesson.student.user
                    )
                    
                    user_timezone = pytz_timezone(other_user.timezone)

                    # Convert start_datetime to the user's local timezone
                    localized_start_datetime = rescheduling_request.original_lesson.start_datetime.astimezone(user_timezone)
                    # Format the datetime for a user-friendly display
                    formatted_datetime = localized_start_datetime.strftime('%d-%m-%Y %I:%M %p')

                    Notification.objects.create(
                        receiver=other_user,    
                        content=f"New rescheduling request for lesson on {formatted_datetime}",
                        timestamp=timezone.now().isoformat(),
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


@login_required
def accept_rescheduling_request(request, rescheduling_request_id):
    rescheduling_request = get_object_or_404(
        ReschedulingRequest, rescheduling_id=rescheduling_request_id
    )

    if request.user.user_type == 1:
        if request.user.student != rescheduling_request.original_lesson.student:
            messages.error(
                request,
                "You don't have permission to accept this rescheduling request.",
            )
            return redirect("lesson_requests")
    elif request.user.user_type == 2:
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
        with transaction.atomic():
            original_lesson = rescheduling_request.original_lesson

            # Create the new lesson
            new_lesson = Lesson.objects.create(
                student=original_lesson.student,
                teacher=original_lesson.teacher,
                start_datetime=rescheduling_request.requested_datetime,
                end_datetime=rescheduling_request.end_datetime,
                student_attendance=False,  # Reset attendance for new lesson
            )

            # Update the original lesson
            original_lesson.is_rescheduled = True
            original_lesson.rescheduled_to = new_lesson
            original_lesson.save()

            # Update the rescheduling request
            rescheduling_request.is_approved = True
            rescheduling_request.save()

            # Create notifications
            Notification.objects.create(
                receiver=original_lesson.student.user,
                content=(
                    f"Lesson on {localtime(original_lesson.start_datetime).strftime("%B %d, %Y at %I:%M %p")} "
                    f"has been rescheduled to {localtime(new_lesson.start_datetime).strftime("%B %d, %Y at %I:%M %p")}"
                ),
            )
            Notification.objects.create(
                receiver=original_lesson.teacher.user,
                content=(
                    f"Lesson on {localtime(original_lesson.start_datetime).strftime("%B %d, %Y at %I:%M %p")} "
                    f"has been rescheduled to {localtime(new_lesson.start_datetime).strftime("%B %d, %Y at %I:%M %p")}"
                ),
            )
        messages.success(request, "The lesson has been successfully rescheduled.")
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("lesson_requests")


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

# Fetches the corresponding schedule based on user type
@login_required
def get_lesson_details(request, lesson_id):
    lesson = get_object_or_404(Lesson, lesson_id=lesson_id)

    if request.user == lesson.student.user:
        # If the current user is the student, fetch the teacher's schedule
        schedule_url = reverse("get_teacher_schedule", args=[lesson.teacher.teacher_id])
    elif request.user == lesson.teacher.user:
        # If the current user is the teacher, fetch the student's schedule
        schedule_url = reverse("get_student_schedule", args=[lesson.student.student_id])
    else:
        return JsonResponse({"error": "Unauthorized access"}, status=403)

    return JsonResponse({"scheduleUrl": schedule_url})
