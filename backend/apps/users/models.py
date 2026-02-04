from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password


class UserManager(BaseUserManager):
  def create_user(self, email_cipher=None, phone_cipher=None, password=None, **extra_fields):
    email_cipher = (email_cipher or '').strip() or None
    phone_cipher = (phone_cipher or '').strip() or None

    if email_cipher:
      email_cipher = self.normalize_email(email_cipher)

    user = self.model(email_cipher=email_cipher, phone_cipher=phone_cipher, **extra_fields)

    if password:
      user.set_password(password)

    user.save(using=self._db)
    return user

  def create_superuser(self, email_cipher, phone_cipher=None, password=None, **extra_fields):
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



