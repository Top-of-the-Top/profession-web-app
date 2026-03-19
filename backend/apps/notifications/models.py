from django.db import models
from django.conf import settings
from apps.courses.models import Course

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=255)
    message = models.TextField()
    is_system = models.BooleanField(default=False)  # Флаг для удобной фильтрации
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
