from django.contrib import admin
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
  list_display = ['user', 'course']
  list_filter = ['user', 'course']
  search_fields = ['user__first_name', 'user__last_name', 'course__title']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
  list_display = ['chat_session', 'content', 'role']
  list_filter = ['chat_session', 'role']
  search_fields = ['chat_session__user__first_name', 'chat_session__user__last_name', 'chat_session__course__title', 'content']