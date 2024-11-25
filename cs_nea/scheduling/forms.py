from django import forms
from .models import LessonRequest, Lesson, ReschedulingRequest
from users.models import Teacher, Student, Invite
from django.utils import timezone
from pytz import timezone as pytz_timezone
import pytz


# Lesson request form for students
class StudentLessonRequestForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.none(),
        empty_label="Select a teacher",
        widget=forms.Select(attrs={"class": "form-control", "id": "teacher-select"}),
    )

    class Meta:
        model = LessonRequest
        fields = [
            "teacher",
            "requested_datetime",
            "end_datetime",
            "request_reason",
            "recurring_amount",
        ]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "recurring_amount": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        user_timezone = self.data.get("timezone")

        if user_timezone:
            user_timezone = pytz_timezone(user_timezone)

            if requested_datetime:
                if requested_datetime.tzinfo is not None:
                    requested_datetime = requested_datetime.replace(tzinfo=None)
                requested_datetime = user_timezone.localize(requested_datetime)
                cleaned_data["requested_datetime"] = requested_datetime.astimezone(
                    pytz.UTC
                )

            if end_datetime:
                if end_datetime.tzinfo is not None:
                    end_datetime = end_datetime.replace(tzinfo=None)
                end_datetime = user_timezone.localize(end_datetime)
                cleaned_data["end_datetime"] = end_datetime.astimezone(pytz.UTC)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop("student", None)
        super(StudentLessonRequestForm, self).__init__(*args, **kwargs)

        if self.student:
            # Get teachers who are connected to the student
            connected_teachers = Teacher.objects.filter(
                sent_invites__student=self.student, 
                sent_invites__status="accepted"
            ).distinct()

            self.fields["teacher"].queryset = connected_teachers
            self.fields["teacher"].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.user.email})"

# Lesson request form for teachers
class TeacherLessonRequestForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        empty_label="Select a student",
        widget=forms.Select(attrs={"class": "form-control", "id": "id_student"}),
    )
    send_request = forms.BooleanField(required=True, initial=True)

    class Meta:
        model = LessonRequest
        fields = [
            "student",
            "requested_datetime",
            "end_datetime",
            "request_reason",
            "recurring_amount",
        ]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "recurring_amount": forms.NumberInput(attrs={"class": "form-control"}),
        }
        
    # Validates the form
    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        user_timezone = self.data.get("timezone")

        if user_timezone:
            user_timezone = pytz_timezone(user_timezone)

            if requested_datetime:
                if requested_datetime.tzinfo is not None:
                    requested_datetime = requested_datetime.replace(tzinfo=None)
                requested_datetime = user_timezone.localize(requested_datetime)
                cleaned_data["requested_datetime"] = requested_datetime.astimezone(
                    pytz.UTC
                )

            if end_datetime:
                if end_datetime.tzinfo is not None:
                    end_datetime = end_datetime.replace(tzinfo=None)
                end_datetime = user_timezone.localize(end_datetime)
                cleaned_data["end_datetime"] = end_datetime.astimezone(pytz.UTC)

        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop("teacher", None)
        super(TeacherLessonRequestForm, self).__init__(*args, **kwargs)

        if self.teacher:
            # Get students who are connected to the teacher         
            connected_students = Student.objects.filter(
                invites__teacher=self.teacher, 
                invites__status="accepted"
            ).distinct()

            self.fields["student"].queryset = connected_students
            self.fields["student"].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.user.email})"


# Corresponding Django form for the Lesson model
class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "student",
            "teacher",
            "start_datetime",
            "end_datetime",
            "student_attendance",
        ]
        # Custom timedate widgets for the form
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "data-tz": timezone.get_current_timezone_name(),
                }
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "data-tz": timezone.get_current_timezone_name(),
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError("Start datetime must be in the future.")
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise forms.ValidationError(
                "End datetime must be after the start datetime."
            )

        return cleaned_data


# Reschedule lesson form
class RescheduleLessonForm(forms.ModelForm):
    lesson = forms.ModelChoiceField(
        queryset=None,
        label="Select Lesson to Reschedule",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = ReschedulingRequest
        fields = ["lesson", "requested_datetime", "end_datetime", "request_reason"]
        widgets = {
            "requested_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "request_reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(RescheduleLessonForm, self).__init__(*args, **kwargs)
        if self.user:
            if self.user.user_type == 1:
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    student=self.user.student, is_rescheduled=False
                ).order_by("start_datetime")
            else:
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    teacher=self.user.teacher, is_rescheduled=False
                ).order_by("start_datetime")

    # Validates the form
    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get("requested_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if requested_datetime and requested_datetime <= timezone.now():
            raise forms.ValidationError("Requested datetime must be in the future.")

        if end_datetime and requested_datetime and end_datetime <= requested_datetime:
            raise forms.ValidationError(
                "End datetime must be after the requested datetime."
            )

        return cleaned_data
