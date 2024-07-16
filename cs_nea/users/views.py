from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from datetime import timedelta
from .forms import (
    LoginForm,
    SignupForm,
    StudentSignupForm,
    TeacherSignupForm,
    TwoFactorForm,
    RetrieveAccountForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    UserSettingsForm,
    InviteForm,
)
from .models import Student, Teacher, User, Invite


def index(request):
    return render(request, "index.html")


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.two_factor_enabled:
                    user.generate_two_factor_code()
                    send_two_factor_code(user)
                    request.session["user_id"] = user.id
                    return redirect("two_factor_verify")
                else:
                    auth_login(request, user)
                    messages.success(request, "You have successfully logged in.")
                    return redirect("dashboard")
            else:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


# 2 factor authentication views
def two_factor_verify(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("index")

    user = User.objects.get(id=user_id)

    if request.method == "POST":
        form = TwoFactorForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get("code")
            if (
                user.two_factor_code == code
                and user.two_factor_code_expiry > timezone.now()
            ):
                auth_login(request, user)
                user.two_factor_code = None
                user.two_factor_code_expiry = None
                user.save()
                messages.success(request, "You have successfully logged in.")
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid or expired code")
    else:
        form = TwoFactorForm()

    return render(request, "users/two_factor_verify.html", {"form": form})


def account_recovery(request):
    if request.method == "POST":
        form = RetrieveAccountForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = User.objects.get(email=email)
                send_password_reset_link(request, user)
                messages.success(
                    request, "A password reset link has been sent to your email."
                )
                return redirect("index")
            except User.DoesNotExist:
                messages.error(request, "No account found with this email address.")
    else:
        form = RetrieveAccountForm()

    return render(request, "users/account_recovery.html", {"form": form})


def send_two_factor_code(user):
    subject = "Your Two-Factor Authentication Code"
    message = f"Your two-factor authentication code is: {user.two_factor_code}"
    send_mail(subject, message, "noreply@example.com", [user.email])


# Account retrieval views
def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = User.objects.get(email=email)
                user.generate_password_reset_token()
                send_password_reset_link(request, user)
                messages.success(
                    request, "A password reset link has been sent to your email."
                )
                return redirect("index")
            except User.DoesNotExist:
                messages.error(request, "No account found with this email address.")
    else:
        form = PasswordResetRequestForm()

    return render(request, "users/password_reset_request.html", {"form": form})


def password_reset(request, token):
    user = get_object_or_404(User, password_reset_token=token)

    # Check if the token has expired (e.g., after 24 hours)
    if user.password_reset_token_created_at < timezone.now() - timedelta(hours=24):
        messages.error(
            request, "The password reset link has expired. Please request a new one."
        )
        return redirect("password_reset_request")

    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get("new_password")
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()
            messages.success(request, "Your password has been reset successfully.")
            return redirect("index")
    else:
        form = PasswordResetForm()

    return render(request, "users/password_reset.html", {"form": form})


@login_required
def enable_disable_2fa(request):
    user = request.user
    if request.method == "POST":
        form = EnableDisable2FAForm(request.POST)
        if form.is_valid():
            enable_2fa = form.cleaned_data.get("enable_2fa")
            user.two_factor_enabled = enable_2fa
            user.save()
            if enable_2fa:
                messages.success(request, "Two-factor authentication has been enabled.")
            else:
                messages.success(
                    request, "Two-factor authentication has been disabled."
                )
            return redirect("settings")
    else:
        form = EnableDisable2FAForm(initial={"enable_2fa": user.two_factor_enabled})

    return render(request, "users/enable_disable_2fa.html", {"form": form})


def send_password_reset_link(request, user):
    user.generate_password_reset_token()
    reset_link = request.build_absolute_uri(
        reverse("password_reset", args=[user.password_reset_token])
    )
    subject = "Password Reset Link"
    message = f"Click the following link to reset your password: {reset_link}"
    send_mail(subject, message, "noreply@example.com", [user.email])


def signup(request):
    if request.path == "/student/signup":
        form_class = StudentSignupForm
        user_type = 1
    elif request.path == "/teacher/signup":
        form_class = TeacherSignupForm
        user_type = 2
    else:
        return redirect("index")  # handle this case as appropriate

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.user_type = user_type
            user.save()

            if user_type == 1:  # Student
                Student.objects.create(
                    user=user,
                    grade_level=form.cleaned_data["grade_level"],
                    extra_student_info=form.cleaned_data.get("extra_student_info", "")
                )
            elif user_type == 2:  # Teacher
                Teacher.objects.create(
                    user=user,
                    extra_teacher_info=form.cleaned_data.get("extra_teacher_info", "")
                )

            messages.success(request, "Your account has been successfully created!")
            return redirect("student_login" if user_type == 1 else "teacher_login")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = form_class()

    return render(request, "users/signup.html", {"form": form})


def logout(request):
    auth_logout(request)
    return redirect("index")


def profile(request):
    return render(request, "users/profile.html")


@login_required
def settings(request):
    user = request.user
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=user)
        if form.is_valid():
            if form.cleaned_data.get("new_password"):
                if user.check_password(form.cleaned_data.get("current_password")):
                    user.set_password(form.cleaned_data.get("new_password"))
                    update_session_auth_hash(request, user)  # Keep the user logged in
                    messages.success(request, "Your password has been updated.")
                else:
                    messages.error(request, "Current password is incorrect.")
                    return render(request, "users/settings.html", {"form": form})

            form.save()
            messages.success(request, "Your settings have been updated.")
            return redirect("settings")
    else:
        form = UserSettingsForm(instance=user)

    return render(request, "users/settings.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.user_type == 2)
def invite_student(request):
    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            message = form.cleaned_data["message"]
            teacher = request.user.teacher

            invite, created = Invite.objects.get_or_create(
                student=student,
                teacher=teacher,
                defaults={"message": message, "status": "pending"},
            )

            if created:
                messages.success(request, f"Invite sent to {student.user.email}")
            else:
                messages.info(request, f"Invite already sent to {student.user.email}")

            return redirect("teacher_dashboard")
    else:
        form = InviteForm()

    return render(request, "users/invite_student.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.user_type == 1)
def student_invites(request):
    student = request.user.student
    pending_invites = Invite.objects.filter(student=student, status="pending")
    return render(request, "users/student_invites.html", {"invites": pending_invites})


@login_required
@user_passes_test(lambda u: u.user_type == 1)
def accept_invite(request, invite_id):
    invite = get_object_or_404(
        Invite, id=invite_id, student=request.user.student, status="pending"
    )
    invite.status = "accepted"
    invite.save()
    messages.success(
        request, f"You are now connected with {invite.teacher.user.get_full_name()}"
    )
    return redirect("student_dashboard")


@login_required
@user_passes_test(lambda u: u.user_type == 2)
def teacher_students(request):
    teacher = request.user.teacher
    accepted_invites = Invite.objects.filter(teacher=teacher, status="accepted")
    students = [invite.student for invite in accepted_invites]
    return render(request, "users/teacher_students.html", {"students": students})


@login_required
@user_passes_test(lambda u: u.user_type == 1)
def student_teachers(request):
    student = request.user.student
    accepted_invites = Invite.objects.filter(student=student, status="accepted")
    teachers = [invite.teacher for invite in accepted_invites]
    return render(request, "users/student_teachers.html", {"teachers": teachers})
