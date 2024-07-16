# users/urls.py

from django.urls import path
from .views import (
    index,
    login,
    signup,
    logout,
    profile,
    settings,
    two_factor_verify,
    account_recovery,
    password_reset_request,
    password_reset,
)

urlpatterns = [
    path("", index, name="index"),
    path("logout", logout, name="logout"),
    path("student/login", login, name="student_login"),
    path("teacher/login", login, name="teacher_login"),
    path("student/signup", signup, name="student_signup"),
    path("teacher/signup", signup, name="teacher_signup"),
    path("profile", profile, name="user_profile"),
    path("settings", settings, name="settings"),
    # URL for two-factor authentication verification before login, only if 2FA activated in settings
    path("two_factor_verify", two_factor_verify, name="two_factor_verify"),
    path("account_recovery", account_recovery, name="account_recovery"),
    path(
        "password_reset_request", password_reset_request, name="password_reset_request"
    ),
    # Password reset token is passed as a URL parameter, URL only accessed through emailed link
    path('password_reset/<str:token>/', password_reset, name='password_reset'),
]
