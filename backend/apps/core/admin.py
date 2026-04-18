from .models import Attachment
from django.contrib import admin

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
  pass