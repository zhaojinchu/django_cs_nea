# Generated by Django 5.0.6 on 2024-07-20 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonrequest',
            name='is_recurring',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='is_sent_by_teacher',
            field=models.BooleanField(default=False),
        ),
    ]