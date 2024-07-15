from django.urls import path
from . import views

urlpatterns = [
    path("lesson_request", views.lesson_request, name="lesson_request"),
    path("create_lesson", views.create_lesson, name="create_lesson"),
    path("create_other_event", views.create_other_event, name="create_other_event"),
    path("calendar/", views.calendar_view, name="calendar"),
    path('get_calendar_data/', views.get_calendar_data, name='get_calendar_data'),
]
