from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from datetime import date
from .forms import StudentLessonRequestForm, TeacherLessonRequestForm, OtherEventForm, LessonForm
from .models import Student, Teacher, Lesson, OtherEvent, LessonRequest
from .calendar_utils import LessonCalendar
from communications.models import Notification


# Predefined functions to check user type
def is_student(user):
    return user.user_type == 1

def is_teacher(user):
    return user.user_type == 2

# Student lesson request form
@login_required
@user_passes_test(is_student)
def student_lesson_request(request):
    if request.method == "POST":
        form = StudentLessonRequestForm(request.POST)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.student = request.user.student
            lesson_request.save()
            
            if lesson_request.teacher.user.notification_preferences.lesson_requests:
                Notification.objects.create(
                    receiver=lesson_request.teacher.user,
                    content=f"New lesson request from {request.user.get_full_name()}"
                )
            
            messages.success(request, "Lesson request submitted successfully!")
            return redirect("dashboard")
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
            lesson_request.is_sent_by_teacher = True
            
            if form.cleaned_data['send_request']:
                lesson_request.save()
                if lesson_request.student.user.notification_preferences.lesson_requests:
                    Notification.objects.create(
                        receiver=lesson_request.student.user,
                        content=f"New lesson request from {request.user.get_full_name()}"
                    )
                messages.success(request, "Lesson request sent to student.")
            else:
                lesson = Lesson.objects.create(
                    student=lesson_request.student,
                    teacher=request.user.teacher,
                    start_datetime=lesson_request.requested_datetime,
                    end_datetime=lesson_request.requested_datetime + lesson_request.duration,
                    is_recurring=lesson_request.is_recurring
                )
                if lesson_request.student.user.notification_preferences.lessons:
                    Notification.objects.create(
                        receiver=lesson_request.student.user,
                        content=f"New lesson scheduled with {request.user.get_full_name()}"
                    )
                messages.success(request, "Lesson scheduled successfully.")
            
            return redirect("dashboard")
    else:
        form = TeacherLessonRequestForm()

    return render(request, "scheduling/teacher_schedule_lesson.html", {"form": form})

# Create lesson view
def create_lesson(request):
    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.student = Student.objects.get(
                user=request.user
            )  # Assuming the logged-in user is a student
            lesson.save()
            messages.success(request, "Lesson created successfully!")
            return redirect("lesson_list")  # Redirect to a list of lessons or dashboard
    else:
        form = LessonForm()

    return render(request, "scheduling/create_lesson.html", {"form": form})


# Create other event view
def create_other_event(request):
    if request.method == "POST":
        form = OtherEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.teacher = Teacher.objects.get(
                user=request.user
            )  # Assuming the logged-in user is a teacher
            event.save()
            messages.success(request, "Event created successfully!")
            return redirect("dashboard")  # Redirect to a list of events or dashboard
    else:
        form = OtherEventForm()

    return render(request, "scheduling/create_other_event.html", {"form": form})






# Calendar views
@login_required
def calendar_view(request):
    return render(request, 'scheduling/calendar.html')

# Calendar refresh view
@login_required
def get_calendar_data(request):
    year = int(request.GET.get('year'))
    month = int(request.GET.get('month'))
    view_type = request.GET.get('view_type', 'month')
    
    # Fetch events for the entire month
    start_date = date(year, month, 1)
    end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    
    lessons = Lesson.objects.filter(
        start_datetime__gte=start_date,
        start_datetime__lt=end_date
    )
    other_events = OtherEvent.objects.filter(
        start_datetime__gte=start_date,
        start_datetime__lt=end_date
    )
    
    if view_type == 'month':
        cal = LessonCalendar(year, month, lessons=lessons, other_events=other_events)
        html_cal = cal.formatmonth(withyear=True)
    else:  # week view
        week = int(request.GET.get('week', 1))
        cal = LessonCalendar(year, month, week, lessons=lessons, other_events=other_events)
        html_cal = cal.formatweek_view()
    
    return JsonResponse({'calendar_html': html_cal})