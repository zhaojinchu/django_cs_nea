from django.urls import path
from .views import index, login, signup, logout, profile, settings

urlpatterns = [
    path("", index, name="index"),
    path("logout", logout, name="logout"),
    path("student/login", login, name="student_login"),
    path("teacher/login", login, name="teacher_login"),
    path("student/signup", signup, name="student_signup"),
    path("teacher/signup", signup, name="teacher_signup"),
    path("profile", profile, name="user_profile"),
    path("settings", settings, name="settings")
]
