from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Notification
from django.contrib.auth import get_user_model

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
    if request.user.user_type == 1:  # Student
        users = User.objects.filter(user_type=2)  # Teachers
    else:  # Teacher
        users = User.objects.filter(user_type=1)  # Students
    return render(request, "communications/message_list.html", {"users": users})


@login_required
def direct_message(request, user_id):
    other_user = User.objects.get(id=user_id)
    return render(
        request, "communications/direct_message.html", {"other_user": other_user}
    )
