import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("courses", "0017_special_courses"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseApplication",
            fields=[
                (
                    "application_id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "На рассмотрении"),
                            ("approved", "Одобрена"),
                            ("rejected", "Отклонена"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="Статус",
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applications",
                        to="courses.course",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Заявка на курс",
                "verbose_name_plural": "Заявки на курсы",
                "db_table": "course_applications",
                "unique_together": {("user", "course")},
            },
        ),
    ]
