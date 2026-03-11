from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.dispatch import receiver
from django.db.models.signals import pre_delete, pre_save
import os


class UserManager(BaseUserManager):
    def create_user(self, email_cipher=None, phone_cipher=None,
                    password=None, **extra_fields):
        email_cipher = (email_cipher or '').strip() or None
        phone_cipher = (phone_cipher or '').strip() or None

        user = self.model(
            email_cipher=email_cipher,
            phone_cipher=phone_cipher,
            **extra_fields)

        if password:
            user.set_password(password)

        user.save(using=self._db)
        return user

    def create_superuser(self, email_cipher, phone_cipher=None,
                         password=None, **extra_fields):
        if not email_cipher or not (email_cipher or '').strip():
            raise ValueError('Суперпользователю необходимо указать email.')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(
            email_cipher=email_cipher.strip(),
            phone_cipher=None,
            password=password,
            **extra_fields
        )


class User(AbstractUser):
    username = None

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='users_user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='users_user_set',
        related_query_name='user',
    )

    first_name = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    last_name = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    email_cipher = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        error_messages={'unique': 'Пользователь с таким email уже существует'},
        help_text='Введите email',
    )

    phone_cipher = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        error_messages={'unique': 'Пользователь с таким телефоном уже существует'},
        help_text='Введите телефон',
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    reset_token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    reset_token_expires = models.DateTimeField(
        null=True,
        blank=True,
    )

    USERNAME_FIELD = 'email_cipher'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        if self.email_cipher:
            return f"{self.id}: {self.email_cipher[:20]}..."
        elif self.phone_cipher:
            return f"{self.id}: {self.phone_cipher[:15]}..."
        return f'User #{self.id}'


DEFAULT_PROFILE_IMAGE = "users/default_photo_user.png"


def profile_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f'users/profile_{instance.pk}.{ext}'


class Profile(models.Model):
    GENDER_CHOICES = (
        ('М', 'Мужской'),
        ('Ж', 'Женский'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_id = models.AutoField(primary_key=True)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(choices=GENDER_CHOICES, null=True, blank=True)
    avatar = models.ImageField(
        upload_to=profile_image_path,
        blank=True,
        null=True,
        verbose_name='Аватар',
        default=DEFAULT_PROFILE_IMAGE,
    )

    @property
    def avatar_url(self):
        if self.avatar and self.avatar.name != DEFAULT_PROFILE_IMAGE:
            return self.avatar.url
        bucket = os.getenv("AWS_S3_BUCKET_NAME", "your-bucket")
        return f'https://storage.yandexcloud.net/{bucket}/{DEFAULT_PROFILE_IMAGE}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and self.avatar and hasattr(
                self.avatar, 'file') and self.avatar.name != DEFAULT_PROFILE_IMAGE:
            image_file = self.avatar.file
            original_name = getattr(self.avatar, 'name', 'image.jpg')

            self.avatar = None
            super().save(*args, **kwargs)

            ext = original_name.split(
                '.')[-1].lower() if '.' in original_name else 'jpg'
            new_name = f'users/profile_{self.pk}.{ext}'

            image_file.seek(0)
            self.avatar.save(new_name, image_file, save=False)
            super().save(update_fields=['avatar'])
        else:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Учетная запись'
        verbose_name_plural = 'Учетная запись'
        ordering = ['-user__date_joined']

    def __str__(self):
        return f'Profile #{self.profile_id}'


@receiver(pre_save, sender=Profile)
def handle_profile_image_update(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if (old_instance.avatar and old_instance.avatar.name != DEFAULT_PROFILE_IMAGE and
                instance.avatar and instance.avatar != old_instance.avatar):
            old_instance.avatar.delete(save=False)
    except sender.DoesNotExist:
        pass


@receiver(pre_delete, sender=Profile)
def delete_profile_image(sender, instance, **kwargs):
    if instance.avatar and instance.avatar.name != DEFAULT_PROFILE_IMAGE:
        instance.avatar.delete(save=False)
