# Generated by Django 5.0.6 on 2024-07-25 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0009_calendarevent_all_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='is_student_notification_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lesson',
            name='is_teacher_notification_sent',
            field=models.BooleanField(default=False),
        ),
    ]
