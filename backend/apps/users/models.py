from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password


class UserManager(BaseUserManager):
  def create_user(self, email_cipher=None, phone_cipher=None, password=None, **extra_fields):
    if email_cipher:
      email_cipher = self.normalize_email(email_cipher)

    user = self.model(email_cipher=email_cipher, phone_cipher=phone_cipher, **extra_fields)

    if password:
      user.set_password(password)

    user.save(using=self._db)
    return user

  def create_superuser(self, email_cipher, phone_cipher=None, password=None, **extra_fields):
    extra_fields.setdefault('is_staff', True)
    extra_fields.setdefault('is_superuser', True)
    extra_fields.setdefault('is_active', True)

    return self.create_user(
      email_cipher=email_cipher,
      phone_cipher=phone_cipher,
      password=password,
      **extra_fields
    )
    

class User(AbstractUser):
  username = None

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

  password_hash = models.CharField(
    max_length=128, 
    blank=True,
    help_text='Введите пароль',
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
  #REQUIRED_FIELDS = ['phone_cipher'] if phone_cipher else []
  REQUIRED_FIELDS = ['phone_cipher']

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

  @property
  def password(self):
    return self.password_hash

  @password.setter
  def password(self, raw_password):
    self.set_password(raw_password)
  
  def set_password(self, raw_password):
    if raw_password:
      self.password_hash = make_password(raw_password)
  
  def check_password(self, raw_password):
    if not self.password_hash:
      return False
    return check_password(raw_password, self.password_hash)

  def has_usable_password(self):
    return bool(self.password_hash) and self.password_hash.startswith((
      'pbkdf2_', 'bcrypt$', 'argon2'
    ))
