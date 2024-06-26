from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from .forms import LoginForm, SignupForm
from .models import User


def index(request):
    return render(request, "index.html")


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect("index")
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            contact_number = form.cleaned_data.get("contact_number")
            date_of_birth = form.cleaned_data.get("DOB")
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data("last_name")
            email = form.cleaned_data.get("email")

            user = User(
                username=username,
                contact_number=contact_number,
                date_of_birth=date_of_birth,
                first_name=first_name,
                last_name=last_name,
                password=password,
                email=email,
            )
            user.save()

            return redirect("index")
    else:
        form = LoginForm()

    return render(request, "users/signup.html", {"form": form})
