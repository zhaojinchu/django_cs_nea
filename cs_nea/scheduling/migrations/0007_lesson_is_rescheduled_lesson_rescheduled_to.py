# Generated by Django 5.0.6 on 2024-07-23 11:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0006_remove_lessonrequest_is_rescheduling_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='is_rescheduled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lesson',
            name='rescheduled_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rescheduled_from', to='scheduling.lesson'),
        ),
    ]
