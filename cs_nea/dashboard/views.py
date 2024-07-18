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
