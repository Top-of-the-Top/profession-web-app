from .models import Attempt, TaskAnswer, QuestionAnswer
from django.contrib import admin

@admin.register(TaskAnswer)
class TaskAnswerAdmin(admin.ModelAdmin):
    pass 

@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    pass 

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    pass 

