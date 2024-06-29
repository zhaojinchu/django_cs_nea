from django.forms import ModelForm
from django.core.validators import RegexValidator
from .models import User
from django import forms

class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "password"]  
        widgets = {
            "password": forms.PasswordInput()
        }
    
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

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match")

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get("contact_number")
        if not contact_number.startswith('+'):
            raise forms.ValidationError("Contact number must start with a '+' followed by the country code")
        return contact_number

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth.strftime("%d-%m-%Y") != self.data["date_of_birth"]:
            raise forms.ValidationError("Enter a valid date in DD-MM-YYYY format")
        return date_of_birth
