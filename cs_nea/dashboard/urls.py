from django.urls import path
from .views import dashboard, student_dashboard, teacher_dashboard   

# URLS to the default dashboard view
urlpatterns = [
    path("dashboard", dashboard, name="dashboard"),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
]
