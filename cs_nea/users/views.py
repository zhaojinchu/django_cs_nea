from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
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
                messages.success(request, "You have successfully logged in.")
                return redirect('index')
            else:
                messages.error(request, "Invalid email or password")
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
            messages.success(request, "Your account has been successfully created!")
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, "users/signup.html", {"form": form})