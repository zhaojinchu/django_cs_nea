from django.urls import path
from .views import dashboard, student_dashboard, teacher_dashboard   

urlpatterns = [
    path("dashboard", dashboard, name="dashboard"),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
]
