from django.urls import path
from . import views
from .calendar_views import (
    calendar_view,
    get_calendar_data,
    create_event,
    update_event,
    delete_event,
)

urlpatterns = [
    path("create_lesson", views.create_lesson, name="create_lesson"),

    # Path for creating student and teacher lesson requests
    path(
        "student/request_lesson/",
        views.student_lesson_request,
        name="student_lesson_request",
    ),
    path(
        "teacher/request_lesson/",
        views.teacher_lesson_request,
        name="teacher_lesson_request",
    ),
    # Path for accepting and listing lesson requests
    path("lesson_requests/", views.lesson_requests, name="lesson_requests"),
    path(
        "accept_lesson_request/<int:request_id>/",
        views.accept_lesson_request,
        name="accept_lesson_request",
    ),
    # Path for declining lesson requests
    path(
        "decline_lesson_request/<int:request_id>/",
        views.decline_lesson_request,
        name="decline_lesson_request",
    ),
    # Path for rescheduling lesson requests
    path("reschedule_lesson/", views.reschedule_lesson, name="reschedule_lesson"),
    path(
        "accept_rescheduling_request/<int:rescheduling_request_id>/",
        views.accept_rescheduling_request,
        name="accept_rescheduling_request",
    ),
    path(
        "decline_rescheduling_request/<int:rescheduling_request_id>/",
        views.decline_rescheduling_request,
        name="decline_rescheduling_request",
    ),
    # Calendar URLs
    path("calendar/", calendar_view, name="calendar"),
    path("get_calendar_data/", get_calendar_data, name="get_calendar_data"),
    # Calendar AJAX URLs
    path("create_event/", create_event, name="create_event"),
    path("update_event/", update_event, name="update_event"),
    path("delete_event/", delete_event, name="delete_event"),
    
    # Fetching teacher schedule URL
    path('get_teacher_schedule/<int:teacher_id>/', views.get_teacher_schedule, name='get_teacher_schedule'),
]
