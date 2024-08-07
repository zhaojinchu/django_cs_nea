# Generated by Django 5.0.6 on 2024-07-25 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0005_rename_timestamp_note_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationconfig',
            name='lesson_reminder_1hr',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationconfig',
            name='lesson_reminder_24hr',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationconfig',
            name='lesson_reminder_30min',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationconfig',
            name='weekly_summary',
            field=models.BooleanField(default=False),
        ),
    ]
