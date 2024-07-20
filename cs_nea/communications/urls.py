from django.urls import path
from . import views

urlpatterns = [
    # Notification URLs
    path('get-notifications/', views.get_notifications, name='get_notifications'),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    
    # Messaging URLs
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:user_id>/', views.direct_message, name='direct_message'),
]

