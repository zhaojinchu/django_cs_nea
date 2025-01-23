from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator, MinLengthValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.utils.crypto import get_random_string


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    # User types
    USER_TYPE_CHOICES = (
        (1, "Student"),
        (2, "Teacher"),
    )
    user_type = models.PositiveSmallIntegerField(
        choices=USER_TYPE_CHOICES,
        default=1,
    )
    
    # Store timezone
    timezone = models.CharField(max_length=50, default="UTC")

    email = models.EmailField(
        "email address",
        max_length=255,
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
    )
    first_name = models.CharField(
        "first name",
        max_length=150,
        validators=[
            RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid first name (letters only).")
        ],
    )
    last_name = models.CharField(
        "last name",
        max_length=150,
        validators=[
            RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid last name (letters only).")
        ],
    )
    password = models.CharField(
        "password",
        max_length=255,
        validators=[
            MinLengthValidator(8),
            RegexValidator(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$",
                "Password must have at least 8 characters, including a number and a capital letter.",
            ),
        ],
    )

    contact_number = PhoneNumberField()

    date_of_birth = models.DateField("date of birth")

    # Two-factor authentication fields
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_code = models.CharField(max_length=6, blank=True, null=True)
    two_factor_code_expiry = models.DateTimeField(blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, null=True, blank=True)
    password_reset_token_created_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["__all__"]

    # Account authentication and retrival methods
    def generate_password_reset_token(self):
        self.password_reset_token = get_random_string(length=32)
        self.password_reset_token_created_at = timezone.now()
        self.save()

    def generate_two_factor_code(self):
        self.two_factor_code = get_random_string(length=6, allowed_chars="0123456789")
        self.two_factor_code_expiry = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        
    # Full name quick access method
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    # First name quick access method
    def get_first_name(self):
        return self.first_name

    # String representation of the user - method is used for all Django models below
    def __str__(self):
        return self.email


class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    extra_teacher_info = models.TextField(
        "extra / optional teacher information",
        max_length=2000,
        blank=True,  # This field is optional
        null=True,
    )
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"



class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    extra_student_info = models.TextField(
        "extra / optional student information",
        max_length=2000,
        blank=True,  # This field is optional
        null=True,
    )
    grade_level = models.IntegerField(
        "grade level",
        validators=[
            RegexValidator(r"^\d+$", "Enter a valid grade level between 1 and 12.")
        ],
    )
    
    def __str__(self):
        return f"{self.user.get_first_name()} ({self.user.email})"



class Invite(models.Model):
    INVITE_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    )

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="invites"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="sent_invites"
    )
    status = models.CharField(
        max_length=10, choices=INVITE_STATUS_CHOICES, default="pending"
    )
    message = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "teacher")

    def __str__(self):
        return f"Invite from {self.teacher} to {self.student} ({self.status})"
