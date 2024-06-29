from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.http import JsonResponse
from .forms import LoginForm, SignupForm
from .models import User


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
                return JsonResponse(
                    {"success": True, "message": "You have successfully logged in."}
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "Invalid email or password"}
                )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Your account has been created. You can now log in.",
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    else:
        form = SignupForm()

    return render(request, "users/signup.html", {"form": form})
