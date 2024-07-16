from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Student, Teacher, Invite

from phonenumber_field.formfields import SplitPhoneNumberField


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())


class SignupForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    contact_number = SplitPhoneNumberField()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "confirm_password",
            "contact_number",
            "date_of_birth",
        ]
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
                self.add_error("password", error)

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
                raise ValidationError(
                    "You must be at least 10 years old to register. Please have your parent or guardian register for you."
                )
        return date_of_birth


class StudentSignupForm(SignupForm):
    grade_level = forms.IntegerField(
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Enter a grade level between 1 and 12.",
        label="Grade Level",
    )
    extra_student_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        label="Extra Information About You (Optional)",
    )

    class Meta(SignupForm.Meta):
        model = User
        fields = SignupForm.Meta.fields + ["grade_level", "extra_student_info"]


class TeacherSignupForm(SignupForm):
    extra_teacher_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        required=False,
        label="Extra Information About You (Optional)",
    )

    class Meta(SignupForm.Meta):
        model = User
        fields = SignupForm.Meta.fields + ["extra_teacher_info"]


# 2 factor authentication form
class TwoFactorForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )


# Account retrieval forms
class RetrieveAccountForm(forms.Form):
    email = forms.EmailField()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()


class PasswordResetForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(), validators=[validate_password]
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match")

        return cleaned_data

class UserSettingsForm(forms.ModelForm):
    current_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    new_password = forms.CharField(widget=forms.PasswordInput(), required=False, validators=[validate_password])
    confirm_new_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'contact_number', 'two_factor_enabled']
        
    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")
        
        if new_password:
            if not current_password:
                raise forms.ValidationError("Current password is required to set a new password")
            if new_password != confirm_new_password:
                raise forms.ValidationError("New passwords do not match")
        
        return cleaned_data
    
# Invite form
class InviteForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.all())
    message = forms.CharField(widget=forms.Textarea, max_length=500, required=False)


