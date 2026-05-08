from django.contrib import admin

from .models import Profile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email_cipher",
        "phone_cipher",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    search_fields = ("email_cipher", "phone_cipher", "first_name", "last_name")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("profile_id", "user", "avatar_url", "birthday", "gender")
    search_fields = (
        "user__email_cipher",
        "user__phone_cipher",
        "user__first_name",
        "user__last_name",
    )
