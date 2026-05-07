from asgiref.sync import sync_to_async
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .api.constants import MSG_EMAIL_ALREADY_EXISTS, MSG_PHONE_ALREADY_EXISTS


class UserManager(BaseUserManager):
    def create_user(self, email_cipher=None, phone_cipher=None, password=None, **extra_fields):
        email_cipher = (email_cipher or "").strip() or None
        phone_cipher = (phone_cipher or "").strip() or None

        user = self.model(email_cipher=email_cipher, phone_cipher=phone_cipher, **extra_fields)

        if password:
            user.set_password(password)

        user.save(using=self._db)
        return user

    def create_superuser(self, email_cipher, phone_cipher=None, password=None, **extra_fields):
        if not email_cipher or not (email_cipher or "").strip():
            raise ValueError("Суперпользователю необходимо указать email.")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(
            email_cipher=email_cipher.strip(), phone_cipher=None, password=password, **extra_fields
        )


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_MODERATOR = "moderator"

    ROLE_CHOICES = [
        (ROLE_STUDENT, "Студент"),
        (ROLE_TEACHER, "Преподаватель"),
        (ROLE_MODERATOR, "Модератор"),
    ]

    username = None

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="users_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="users_user_set",
        related_query_name="user",
    )

    first_name = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    last_name = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        verbose_name="Роль",
    )

    email_cipher = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        error_messages={"unique": MSG_EMAIL_ALREADY_EXISTS},
        help_text="Введите email",
    )

    phone_cipher = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        error_messages={"unique": MSG_PHONE_ALREADY_EXISTS},
        help_text="Введите телефон",
    )

    date_joined = models.DateTimeField(
        auto_now_add=True,
    )

    reset_token = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    reset_token_expires = models.DateTimeField(
        null=True,
        blank=True,
    )

    USERNAME_FIELD = "email_cipher"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_purchased_courses_ids(self):
        from django.utils import timezone

        return list(
            self.purchased_courses.filter(access_expires_at__gt=timezone.now()).values_list(
                "course_id", flat=True
            )
        )

    async def aget_purchased_course_ids(self):
        return await sync_to_async(self.get_purchased_courses_ids)()

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    def is_moderator(self):
        return self.role == self.ROLE_MODERATOR

    def is_course_author(self, course):
        return self in course.authors.all()

    def is_enrolled(self, course):
        return course.course_id in self.get_purchased_courses_ids()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-date_joined"]

    def __str__(self):
        if self.email_cipher:
            return f"{self.id}: {self.email_cipher[:20]}..."
        elif self.phone_cipher:
            return f"{self.id}: {self.phone_cipher[:15]}..."
        return f"User #{self.id}"


class Profile(models.Model):
    GENDER_CHOICES = (
        ("М", "Мужской"),
        ("Ж", "Женский"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_id = models.AutoField(primary_key=True)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default="")
    avatar_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="URL аватара (legacy)",
    )

    class Meta:
        verbose_name = "Учетная запись"
        verbose_name_plural = "Учетная запись"
        ordering = ["-user__date_joined"]

    def __str__(self):
        return f"Profile #{self.profile_id}"
