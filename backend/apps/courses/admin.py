from django.contrib import admin
from .models import Course, Lesson, Homework

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('id', 'title', 'slug')
    search_fields = ('title',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}




