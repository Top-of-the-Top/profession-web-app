from django.db import models
from dango.contrib.auth.models import AbstractUser, BaseUserManager




class User(AbstractUser):
  username = None
  email = models.EmailField(unique=True)
  phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
  role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
  first_name = models.CharField(max_length=30, null=True, blank=True)
  last_name = models.CharField(max_length=30, null=True, blank=True)
  password = models.
  
  is_active = models.BooleanField(default=True)
  is_staff = models.BooleanField(default=False)
  is_superuser = models.BooleanField(default=False)
  is_verified = models.BooleanField(default=False)

  def __str__(self) -> str:
    return self.emai

