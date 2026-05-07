from django.contrib import admin

from .models import Chat, Message, Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["user", "course"]
    list_filter = ["user", "course"]
    search_fields = ["user__first_name", "user__last_name", "course__title"]


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = []


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["chat", "content", "role"]
    list_filter = ["chat", "role"]
    search_fields = [
        "chat__session__user__first_name",
        "chat__session__user__last_name",
        "chat__session__course__title",
        "content",
    ]
