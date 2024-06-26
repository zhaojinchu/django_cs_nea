from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    contact_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    # Name, Username, Password, and Email are already included in AbstractUser

class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    teacher_information = models.TextField()

class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_information = models.TextField()
    grade_level = models.CharField(max_length=50)

class Invite(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    invite_status = models.CharField(max_length=20)
    message = models.TextField()
    date_of_invite = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'teacher')