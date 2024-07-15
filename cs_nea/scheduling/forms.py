from django import forms
from .models import LessonRequest, Lesson, OtherEvent
from django.utils import timezone
from datetime import timedelta

# Corresponding Django form for the LessonRequest model
class LessonRequestForm(forms.ModelForm):
    class Meta:
        model = LessonRequest
        fields = ['teacher', 'requested_datetime', 'is_rescheduling', 'request_reason', 'duration', 'recurring_amount']
        widgets = {
            'requested_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'duration': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_requested_datetime(self):
        requested_datetime = self.cleaned_data.get('requested_datetime')
        if requested_datetime <= timezone.now():
            raise forms.ValidationError("Requested datetime must be in the future.")
        return requested_datetime

    def clean_request_reason(self):
        request_reason = self.cleaned_data.get('request_reason')
        if not request_reason.strip():
            raise forms.ValidationError("Request reason cannot be empty or just whitespace.")
        return request_reason

    def clean_duration(self):
        duration = self.cleaned_data.get('duration')
        if duration < timedelta(minutes=15) or duration > timedelta(hours=3):
            raise forms.ValidationError("Duration must be between 15 minutes and 3 hours.")
        return duration

    def clean_recurring_amount(self):
        recurring_amount = self.cleaned_data.get('recurring_amount')
        if recurring_amount < 1 or recurring_amount > 52:
            raise forms.ValidationError("Recurring amount must be between 1 and 52.")
        return recurring_amount
    
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