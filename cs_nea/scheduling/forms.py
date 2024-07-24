from django import forms
from .models import LessonRequest, Lesson, ReschedulingRequest
from django.utils import timezone

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
            "requested_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
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
            "requested_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
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
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", "data-tz": timezone.get_current_timezone_name()}),
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
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ReschedulingRequest
        fields = ['lesson', 'requested_datetime', 'end_datetime', 'request_reason']
        widgets = {
            'requested_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'request_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(RescheduleLessonForm, self).__init__(*args, **kwargs)
        if self.user:
            if self.user.user_type == 1:  
                self.fields['lesson'].queryset = Lesson.objects.filter(student=self.user.student, is_rescheduled=False).order_by('start_datetime')
            else:   
                self.fields['lesson'].queryset = Lesson.objects.filter(teacher=self.user.teacher, is_rescheduled=False).order_by('start_datetime')

    def clean(self):
        cleaned_data = super().clean()
        requested_datetime = cleaned_data.get('requested_datetime')
        end_datetime = cleaned_data.get('end_datetime')

        if requested_datetime and requested_datetime <= timezone.now():
            raise forms.ValidationError("Requested datetime must be in the future.")

        if end_datetime and requested_datetime and end_datetime <= requested_datetime:
            raise forms.ValidationError("End datetime must be after the requested datetime.")

        return cleaned_data
