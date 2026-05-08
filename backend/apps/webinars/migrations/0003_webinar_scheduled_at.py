from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webinars", "0002_recording_duration_seconds"),
    ]

    operations = [
        migrations.AddField(
            model_name="webinar",
            name="scheduled_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Запланированное начало",
            ),
        ),
    ]
