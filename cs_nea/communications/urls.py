from django.urls import path
from . import views

urlpatterns = [
    # Notification URLs
    path('get-notifications/', views.get_notifications, name='get_notifications'),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    
    # Messaging URLs
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:user_id>/', views.direct_message, name='direct_message'),
    
    # Assignment URLs
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.create_assignment, name='create_assignment'),
    path('assignments/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:assignment_id>/complete/', views.mark_completed, name='mark_completed'),
]

