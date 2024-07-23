from django import forms
from .models import LessonRequest, Lesson, OtherEvent
from django.utils import timezone
from datetime import timedelta
from users.models import Teacher, Student


# Lesson request form for students
class StudentLessonRequestForm(forms.ModelForm):
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
            "requested_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


# Lesson request form for teachers
class TeacherLessonRequestForm(forms.ModelForm):
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
            "requested_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


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
        widgets = {
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
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


# Corresponding Django form for the OtherEvent model
class OtherEventForm(forms.ModelForm):
    class Meta:
        model = OtherEvent
        fields = [
            "teacher",
            "start_datetime",
            "end_datetime",
            "event_description",
            "recurring_amount",
        ]

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        event_description = cleaned_data.get("event_description")
        recurring_amount = cleaned_data.get("recurring_amount")

        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError("Start datetime must be in the future.")
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise forms.ValidationError(
                "End datetime must be after the start datetime."
            )
        if not event_description or not event_description.strip():
            raise forms.ValidationError(
                "Event description cannot be empty or just whitespace."
            )
        if recurring_amount and (recurring_amount < 1 or recurring_amount > 52):
            raise forms.ValidationError("Recurring amount must be between 1 and 52.")


# Reschedule lesson form
class RescheduleLessonForm(forms.ModelForm):
    lesson = forms.ModelChoiceField(
        queryset=None,
        label="Select Lesson to Reschedule",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = LessonRequest
        fields = ["lesson", "requested_datetime", "end_datetime", "request_reason"]
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
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(RescheduleLessonForm, self).__init__(*args, **kwargs)
        if user:
            if user.user_type == 1:  # Student
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    student=user.student
                ).order_by("start_datetime")
            else:  # Teacher
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    teacher=user.teacher
                ).order_by("start_datetime")
