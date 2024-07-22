from django.urls import path
from . import views

urlpatterns = [
    path("create_lesson", views.create_lesson, name="create_lesson"),
    path("create_other_event", views.create_other_event, name="create_other_event"),
    path("calendar/", views.calendar_view, name="calendar"),
    path('get_calendar_data/', views.get_calendar_data, name='get_calendar_data'),
    
    # Path for creating student and teacher lesson requests
    path('student/request_lesson/', views.student_lesson_request, name='student_lesson_request'),
    path('teacher/request_lesson/', views.teacher_lesson_request, name='teacher_lesson_request'),
    
    # Path for accepting and listing lesson requests
    path('lesson_requests/', views.lesson_requests, name='lesson_requests'),
    path('accept_lesson_request/<int:request_id>/', views.accept_lesson_request, name='accept_lesson_request'),
    
    # Path for declining lesson requests
    path('decline_lesson_request/<int:request_id>/', views.decline_lesson_request, name='decline_lesson_request'),
    
    # Path for rescheduling lesson requests
    path('reschedule_lesson/', views.reschedule_lesson, name='reschedule_lesson'),
]


