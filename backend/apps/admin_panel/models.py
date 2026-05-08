import secrets
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.users.models import User

INVITE_TTL_DAYS = 3


class TeacherInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(verbose_name="Email приглашённого")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invites",
        verbose_name="Кто создал",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Истекает")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Использован")

    class Meta:
        verbose_name = "Приглашение преподавателя"
        verbose_name_plural = "Приглашения преподавателей"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=INVITE_TTL_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def status(self):
        if self.is_used:
            return "used"
        if self.is_expired:
            return "expired"
        return "pending"

    def __str__(self):
        return f"Invite({self.email}, {self.status})"
