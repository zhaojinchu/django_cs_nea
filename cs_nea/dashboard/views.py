from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test


# Predefined functions to check user type
def is_student(user):
    return user.user_type == 1


def is_teacher(user):
    return user.user_type == 2


# Dashboard redirect to teacher or student dashboard
@login_required
def dashboard(request):
    if request.user.user_type == 1:  # Student
        return redirect("student_dashboard")
    elif request.user.user_type == 2:  # Teacher
        return redirect("teacher_dashboard")
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
