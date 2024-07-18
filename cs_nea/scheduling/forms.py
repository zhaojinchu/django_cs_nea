from django import forms
from .models import LessonRequest, Lesson, OtherEvent
from django.utils import timezone
from datetime import timedelta
from users.models import Teacher, Student

# Lesson request form for students
class StudentLessonRequestForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(queryset=Teacher.objects.all())

    class Meta:
        model = LessonRequest
        fields = ['teacher', 'requested_datetime', 'request_reason', 'duration', 'is_recurring', 'recurring_amount']
        widgets = {
            'requested_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'duration': forms.TimeInput(attrs={'type': 'time'}),
        }

# Lesson request form for teachers
class TeacherLessonRequestForm(forms.ModelForm):
    student = forms.ModelChoiceField(queryset=Student.objects.all())
    send_request = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = LessonRequest
        fields = ['student', 'requested_datetime', 'request_reason', 'duration', 'is_recurring', 'recurring_amount']
        widgets = {
            'requested_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'duration': forms.TimeInput(attrs={'type': 'time'}),
        }
    
# Corresponding Django form for the Lesson model
class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['student', 'teacher', 'start_datetime', 'end_datetime', 'student_attendance']

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')

        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError("Start datetime must be in the future.")
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise forms.ValidationError("End datetime must be after the start datetime.")

# Corresponding Django form for the OtherEvent model
class OtherEventForm(forms.ModelForm):
    class Meta:
        model = OtherEvent
        fields = ['teacher', 'start_datetime', 'end_datetime', 'event_description', 'recurring_amount']

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        event_description = cleaned_data.get('event_description')
        recurring_amount = cleaned_data.get('recurring_amount')

        if start_datetime and start_datetime <= timezone.now():
            raise forms.ValidationError("Start datetime must be in the future.")
        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise forms.ValidationError("End datetime must be after the start datetime.")
        if not event_description or not event_description.strip():
            raise forms.ValidationError("Event description cannot be empty or just whitespace.")
        if recurring_amount and (recurring_amount < 1 or recurring_amount > 52):
            raise forms.ValidationError("Recurring amount must be between 1 and 52.")