from django.urls import path
from .views import index, login, signup, logout, student, teacher

urlpatterns = [
    path("", index, name="index"),
    path("logout/", logout, name="logout"),
    path("student/", student, name="student"),
    path("teacher/", teacher, name="teacher"),
    path("student/login", login, name="student_login"),
    path("teacher/login", login, name="teacher_login"),
    path("student/signup", signup, name="student_signup"),
    path("teacher/signup", signup, name="teacher_signup"),
]
