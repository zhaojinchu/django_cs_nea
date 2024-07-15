from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from .forms import LoginForm, SignupForm, StudentSignupForm, TeacherSignupForm
from .models import Student, Teacher

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
                auth_login(request, user)
                messages.success(request, "You have successfully logged in.")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})

def signup(request):
    if request.path == "/student/signup":
        form_class = StudentSignupForm
        user_type = 1
    elif request.path == "/teacher/signup":
        form_class = TeacherSignupForm
        user_type = 2
    else:
        return redirect('index')  # handle this case as appropriate

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.user_type = user_type
            user.save()

            if isinstance(form, StudentSignupForm):
                Student.objects.create(
                    user=user,
                    grade_level=form.cleaned_data['grade_level'],
                    extra_student_info=form.cleaned_data['extra_student_info']
                )
            elif isinstance(form, TeacherSignupForm):
                Teacher.objects.create(
                    user=user,
                    extra_teacher_info=form.cleaned_data['extra_teacher_info']
                )

            messages.success(request, "Your account has been successfully created!")
            if request.path == "/student/signup":
                return redirect("student_login")
            elif request.path == "/teacher/signup":
                return redirect("teacher_login")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = form_class()

    return render(request, "users/signup.html", {"form": form})

def logout(request):
    auth_logout(request)
    return redirect('index')

def profile(request):
    return render(request, "users/profile.html")

def settings(request):
    return render(request, "users/settings.html")