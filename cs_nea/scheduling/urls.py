from django.urls import path
from . import views

urlpatterns = [
    path("create_lesson", views.create_lesson, name="create_lesson"),
    path("create_other_event", views.create_other_event, name="create_other_event"),
    path("calendar/", views.calendar_view, name="calendar"),
    path('get_calendar_data/', views.get_calendar_data, name='get_calendar_data'),
    
    path('student/request_lesson/', views.student_lesson_request, name='student_lesson_request'),
    path('teacher/request_lesson/', views.teacher_lesson_request, name='teacher_lesson_request'),
]


