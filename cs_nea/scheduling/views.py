from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LessonRequestForm, OtherEventForm, LessonForm
from .models import Student, Teacher, Lesson, OtherEvent


# Lesson request view
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


# Calendar view
def calendar_view(request):
    lessons = Lesson.objects.all()
    other_events = OtherEvent.objects.all()

    # You might want to add filtering based on the logged-in user or date range
    # For example:
    # if request.user.is_student:
    #     lessons = lessons.filter(student__user=request.user)
    # elif request.user.is_teacher:
    #     lessons = lessons.filter(teacher__user=request.user)
    #     other_events = other_events.filter(teacher__user=request.user)

    context = {
        "lessons": lessons,
        "other_events": other_events,
    }
    return render(request, "scheduling/calendar.html", context)
