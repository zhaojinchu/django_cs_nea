# Generated by Django 5.0.6 on 2024-07-15 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_user_contact_number_alter_user_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='user_type',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Student'), (2, 'Teacher')], default=1),
        ),
    ]
