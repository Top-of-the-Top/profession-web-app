# Generated migration for adding role field to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('student', 'Студент'),
                    ('teacher', 'Преподаватель'),
                    ('moderator', 'Модератор')
                ],
                default='student',
                max_length=20,
                verbose_name='Роль'
            ),
        ),
    ]
