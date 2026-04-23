from .models import Course, Section, Lesson, Homework, Task, Question, PurchasedCourse
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']

    list_filter = ['price']
    prepopulated_fields = {'slug': ('title',)}
    list_display = ['title_link', 'price', 'image_preview']
    list_per_page = 25

    readonly_fields = ['image_preview', 'kinescope_folder_id']

    def title_link(self, obj):
        """Кликабельное название → сразу на страницу курса"""
        url = reverse('admin:courses_course_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.title)

    title_link.short_description = 'Название курса'

    def image_preview(self, obj):
        """Миниатюра картинки"""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height: 50px;" />', obj.image_url)
        return "Нет картинки"

    image_preview.short_description = 'Изображение'

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    pass


@admin.register(PurchasedCourse)
class PurchasedCourseAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'course',
        'payment',
        'access_expires_at',
        'is_active')
    list_filter = ('access_expires_at',)
    search_fields = ('user__email_cipher', 'course__title')
