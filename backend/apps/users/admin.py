from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
  list_display = ('id', 'email_cipher', 'phone_cipher', 'first_name', 'last_name', 'is_staff', 'is_active')
  search_fields = ('email_cipher', 'phone_cipher', 'first_name', 'last_name')
