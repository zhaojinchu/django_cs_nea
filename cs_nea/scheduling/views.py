from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
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
)
from communications.models import Notification
from datetime import timedelta
from django.db import transaction
from communications.models import Notification, NotificationConfig
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from django.utils import timezone

def is_teacher(user):
    return user.user_type == 2


def is_student(user):
    return user.user_type == 1


# Student lesson request form
@login_required
@user_passes_test(is_student)
def student_lesson_request(request):
    if request.method == "POST":
        form = StudentLessonRequestForm(request.POST)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.student = request.user.student
            lesson_request.is_rescheduling = False
            
            # Conversion to UTC time
            lesson_request.requested_datetime = make_aware(form.cleaned_data['requested_datetime'])
            lesson_request.end_datetime = make_aware(form.cleaned_data['end_datetime'])
            
            lesson_request.save()

            teacher = lesson_request.teacher
            # Get or create NotificationConfig for the teacher
            notification_config, created = NotificationConfig.objects.get_or_create(
                user=teacher.user
            )

            if notification_config.receive_notification:
                recurring_text = (
                    f" (recurring {lesson_request.recurring_amount} times)"
                    if lesson_request.recurring_amount > 1
                    else ""
                )
                Notification.objects.create(
                    receiver=teacher.user,
                    content=f"New lesson request from {request.user.get_full_name()}{recurring_text}",
                )

            messages.success(request, "Lesson request submitted successfully!")
            return redirect("dashboard")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentLessonRequestForm()

    return render(request, "scheduling/student_schedule_lesson.html", {"form": form})


# Teacher lesson request form
@login_required
@user_passes_test(is_teacher)
def teacher_lesson_request(request):
    if request.method == "POST":
        form = TeacherLessonRequestForm(request.POST)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.teacher = request.user.teacher
            lesson_request.is_rescheduling = False
            lesson_request.is_sent_by_teacher = True
            
            lesson_request.requested_datetime = make_aware(form.cleaned_data['requested_datetime'])
            lesson_request.end_datetime = make_aware(form.cleaned_data['end_datetime'])

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
                    Notification.objects.create(
                        receiver=student.user,
                        content=f"New lesson request from {request.user.get_full_name()}{recurring_text}",
                    )

                messages.success(request, "Lesson request sent to student.")
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
                    Notification.objects.create(
                        receiver=lesson_request.student.user,
                        content=f"New lesson{recurring_text} scheduled with {request.user.get_full_name()}",
                    )
                messages.success(
                    request,
                    f"{lesson_request.recurring_amount} lesson{'s' if lesson_request.recurring_amount > 1 else ''} scheduled successfully.",
                )

            return redirect("dashboard")
    else:
        form = TeacherLessonRequestForm()

    return render(request, "scheduling/teacher_schedule_lesson.html", {"form": form})


# Create lesson view
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


# View for listing lessons requests
@login_required
def lesson_requests(request):
    if request.user.user_type == 1:  # Student
        scheduling_requests = LessonRequest.objects.filter(
            student=request.user.student, is_approved=False
        )
        rescheduling_requests = ReschedulingRequest.objects.filter(
            original_lesson__student=request.user.student, is_approved=False
        )
    else:  # Teacher
        scheduling_requests = LessonRequest.objects.filter(
            teacher=request.user.teacher, is_approved=False
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
                    start_datetime=timezone.make_aware(start_time),
                    end_datetime=timezone.make_aware(end_time),
                    request=lesson_request,
                )

            lesson_request.is_approved = True
            lesson_request.save()

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
