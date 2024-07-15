from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LessonRequestForm, OtherEventForm, LessonForm
from .models import Student, Teacher
from django.contrib.auth.decorators import login_required, user_passes_test
from .calendar_utils import LessonCalendar
from django.http import JsonResponse

# Predefined functions to check user type
def is_student(user):
    return user.user_type == 1

def is_teacher(user):
    return user.user_type == 2

# Lesson request view for students
@login_required
@user_passes_test(is_student)
def lesson_request(request):
    if request.method == "POST":
        form = LessonRequestForm(request.POST)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.student = Student.objects.get(
                user=request.user
            )  # Assuming the logged-in user is a student
            lesson_request.save()
            messages.success(request, "Lesson request submitted successfully!")
            return redirect(
                "dashboard"
            )  # Or wherever you want to redirect after successful submission
    else:
        form = LessonRequestForm()

    return render(request, "scheduling/schedule_lesson.html", {"form": form})

# Lesson request view for teachers
@login_required
@user_passes_test(is_teacher)
def lesson_request(request):
    if request.method == "POST":
        form = LessonRequestForm(request.POST)
        if form.is_valid():
            lesson_request = form.save(commit=False)
            lesson_request.student = Student.objects.get(
                user=request.user
            )  # Assuming the logged-in user is a student
            lesson_request.save()
            messages.success(request, "Lesson request submitted successfully!")
            return redirect(
                "dashboard"
            )  # Or wherever you want to redirect after successful submission
    else:
        form = LessonRequestForm()

    return render(request, "scheduling/schedule_lesson.html", {"form": form})

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
    
    if view_type == 'month': # month view
        cal = LessonCalendar(year, month)
        html_cal = cal.formatmonth(withyear=True)
    else:  # week view
        week = int(request.GET.get('week', 1))
        cal = LessonCalendar(year, month, week)
        html_cal = cal.formatweek_view()
    
    return JsonResponse({'calendar_html': html_cal})