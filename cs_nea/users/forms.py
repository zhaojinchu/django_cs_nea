from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    
class SignupForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password", "confirm_password", "contact_number", "date_of_birth"]
        widgets = {
            "password": forms.PasswordInput(),
            "date_of_birth": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match")
            try:
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error('password', error)

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
             raise ValidationError("Email already exists")
        return email

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth:
            from datetime import date
            age = (date.today() - date_of_birth).days // 365
            if age < 10:
                raise ValidationError("You must be at least 10 years old to register. Please have your parent or guardian register for you.")
        return date_of_birth