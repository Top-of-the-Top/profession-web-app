from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Chat, Message, Session


class ChatInline(TabularInline):
    model = Chat
    extra = 0
    readonly_fields = ("chat_id", "title", "messages_count", "updated_at")
    fields = ("chat_id", "title", "messages_count", "updated_at")
    show_change_link = True

    def messages_count(self, obj):
        return obj.messages.count()

    messages_count.short_description = "Сообщений"


class MessageInline(TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role_badge", "content_preview", "created_at")
    fields = ("role_badge", "content_preview", "created_at")
    can_delete = False

    def role_badge(self, obj):
        color = "#0ea5e9" if obj.role == "user" else "#8b5cf6"
        label = obj.get_role_display()
        return format_html(
            '<span style="padding:2px 8px;border-radius:4px;font-size:11px;'
            'background:{};color:#fff;">{}</span>',
            color,
            label,
        )

    def content_preview(self, obj):
        text = obj.content[:120]
        if len(obj.content) > 120:
            text += "…"
        return text

    role_badge.short_description = "Роль"
    content_preview.short_description = "Сообщение"


@admin.register(Session)
class SessionAdmin(ModelAdmin):
    list_display = (
        "session_short_id",
        "user_link",
        "course_link",
        "chats_count",
        "created_at",
    )
    list_filter = ("course", "created_at")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email_cipher",
        "course__title",
    )
    readonly_fields = ("session_id", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [ChatInline]

    fieldsets = (
        (
            "Сессия",
            {
                "fields": ("session_id", "user", "course"),
            },
        ),
        (
            "Даты",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="ID")
    def session_short_id(self, obj):
        return str(obj.session_id)[:8] + "…"

    @display(description="Пользователь")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip() or str(obj.user)
        return format_html('<a href="{}">{}</a>', url, name)

    @display(description="Курс")
    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @display(description="Чатов")
    def chats_count(self, obj):
        return obj.chats.count()


@admin.register(Chat)
class ChatAdmin(ModelAdmin):
    list_display = (
        "chat_short_id",
        "title_display",
        "session_link",
        "messages_count",
        "updated_at",
    )
    search_fields = (
        "title",
        "session__user__first_name",
        "session__user__email_cipher",
        "session__course__title",
    )
    readonly_fields = ("chat_id", "created_at", "updated_at")
    ordering = ("-updated_at",)
    inlines = [MessageInline]

    fieldsets = (
        (
            "Чат",
            {
                "fields": ("chat_id", "session", "title"),
            },
        ),
        (
            "Даты",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="ID")
    def chat_short_id(self, obj):
        return str(obj.chat_id)[:8] + "…"

    @display(description="Название")
    def title_display(self, obj):
        return obj.title or "—"

    @display(description="Сессия")
    def session_link(self, obj):
        url = reverse("admin:ai_chat_bot_session_change", args=[obj.session_id])
        return format_html(
            '<a href="{}">{}  →  {}</a>',
            url,
            str(obj.session.user),
            obj.session.course.title,
        )

    @display(description="Сообщений")
    def messages_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = (
        "message_short_id",
        "role_badge",
        "chat_link",
        "content_preview",
        "created_at",
    )
    list_filter = ("role",)
    search_fields = (
        "content",
        "chat__session__user__first_name",
        "chat__session__user__email_cipher",
        "chat__session__course__title",
    )
    readonly_fields = ("message_id", "created_at", "updated_at")
    ordering = ("-created_at",)

    @display(description="ID")
    def message_short_id(self, obj):
        return str(obj.message_id)[:8] + "…"

    @display(description="Роль", label=True)
    def role_badge(self, obj):
        colors = {"user": "blue", "assistant": "purple"}
        return obj.get_role_display(), colors.get(obj.role, "gray")

    @display(description="Чат")
    def chat_link(self, obj):
        url = reverse("admin:ai_chat_bot_chat_change", args=[obj.chat_id])
        title = obj.chat.title or str(obj.chat_id)[:8]
        return format_html('<a href="{}">{}</a>', url, title)

    @display(description="Сообщение")
    def content_preview(self, obj):
        text = obj.content[:100]
        return text + "…" if len(obj.content) > 100 else text
