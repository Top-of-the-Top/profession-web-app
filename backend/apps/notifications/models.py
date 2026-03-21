from django.db import models
from django.conf import settings
from apps.courses.models import Course


class Notification(models.Model):
    PERSONAL = 'personal'
    COURSE = 'course'
    SYSTEM = 'system'

    NOTIFICATION_TYPES = [
        (PERSONAL, 'Личное'),
        (COURSE, 'Курс'),
        (SYSTEM, 'Системное'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True, blank=True
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='course_notifications'
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default=PERSONAL
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    html_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user',]),
            models.Index(fields=['course', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title}"