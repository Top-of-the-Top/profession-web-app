from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_add_courses_authors'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='read_by',
            field=models.ManyToManyField(
                blank=True,
                related_name='read_notifications',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
