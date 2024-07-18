from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(receiver=request.user, is_read=False).order_by('-timestamp')[:20]
    data = [{
        'id': notif.id,
        'content': notif.content,
        'timestamp': notif.timestamp.strftime('%Y-%m-%d %H:%M')
    } for notif in notifications]
    return JsonResponse(data, safe=False)

@require_POST
@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, receiver=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)