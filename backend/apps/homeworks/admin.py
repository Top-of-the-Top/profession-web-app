from django.contrib import admin

from .models import Attempt, QuestionAnswer, TaskAnswer


@admin.register(TaskAnswer)
class TaskAnswerAdmin(admin.ModelAdmin):
    pass


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    pass


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    pass
