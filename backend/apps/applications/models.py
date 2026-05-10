import uuid

from django.db import models

from apps.courses.models import Course
from apps.users.models import User


class CourseApplication(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "На рассмотрении"),
        (APPROVED, "Одобрена"),
        (REJECTED, "Отклонена"),
    ]

    application_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_applications",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name="Статус",
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_applications"
        verbose_name = "Заявка на курс"
        verbose_name_plural = "Заявки на курсы"
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} → {self.course} [{self.status}]"
