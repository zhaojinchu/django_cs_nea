from django import forms
from .models import Assignment, NotificationConfig
from users.models import Student


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["student", "task_content", "due_date"]
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop("teacher", None)
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields["student"].queryset = Student.objects.filter(
                invites__teacher=self.teacher, invites__status="accepted"
            )


class NotificationConfigForm(forms.ModelForm):
    class Meta:
        model = NotificationConfig
        fields = [
            "receive_notification",
            "lesson_reminder",
            "assignment_notification",
            "message_notification",
            "attendance_notification",
            "t2r_requests",
            "cancellation_notification",
            "weekly_summary",
            "lesson_reminder_1hr",
            "lesson_reminder_24hr",
            "lesson_reminder_30min",
        ]
