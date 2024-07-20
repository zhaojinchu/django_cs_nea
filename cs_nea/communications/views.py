from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Notification, Assignment
from django.contrib.auth import get_user_model
from .forms import AssignmentForm
from django.utils import timezone


User = get_user_model()


# Notification views - only JSON responses
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
    if request.user.user_type == 1: 
        users = User.objects.filter(user_type=2)  
    else:  
        users = User.objects.filter(user_type=1) 
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


@login_required
@user_passes_test(lambda u: u.user_type == 1)
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
