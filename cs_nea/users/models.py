from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator, MinLengthValidator
from phonenumber_field.modelfields import PhoneNumberField

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
    email = models.EmailField(
        "email address",
        max_length=255,
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
    )
    first_name = models.CharField(
        "first name",
        max_length=150,
        validators=[RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid first name (letters only).")],
    )
    last_name = models.CharField(
        "last name",
        max_length=150,
        validators=[RegexValidator(r"^[a-zA-Z\s]+$", "Enter a valid last name (letters only).")],
    )
    password = models.CharField(
        "password",
        max_length=255,
        validators=[
            MinLengthValidator(6),
            RegexValidator(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{6,}$",
                "Password must have at least 6 characters, including a number and a capital letter.",
            ),
        ],
    )
    contact_number = PhoneNumberField()
    
    date_of_birth = models.DateField("date of birth")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["__all__"]

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


class Invite(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    invite_status = models.CharField(max_length=20)
    messages_sent = models.TextField("content of messages sent", max_length=2000)
    date_of_invite = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "teacher")
