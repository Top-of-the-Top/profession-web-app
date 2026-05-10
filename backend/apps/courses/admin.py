from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Course, CourseEnrollment, Homework, Lesson, Question, Section, Task


class SectionInline(TabularInline):
    model = Section
    extra = 0
    fields = ("section_number", "title", "type", "created_at")
    readonly_fields = ("section_number", "created_at")
    show_change_link = True


class LessonInline(TabularInline):
    model = Lesson
    extra = 0
    fields = ("lesson_number", "title", "type", "created_at")
    readonly_fields = ("lesson_number", "created_at")
    show_change_link = True


class HomeworkInline(TabularInline):
    model = Homework
    extra = 0
    fields = ("homework_number", "title", "deadline", "max_points")
    readonly_fields = ("homework_number",)
    show_change_link = True


class QuestionInline(TabularInline):
    model = Question
    extra = 0
    fields = ("question_number", "text", "correct_ans", "max_points")
    readonly_fields = ("question_number",)


class TaskInline(TabularInline):
    model = Task
    extra = 0
    fields = ("task_number", "text", "max_points")
    readonly_fields = ("task_number",)


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = (
        "image_thumb",
        "title_link",
        "status_badge",
        "price_display",
        "authors_list",
        "purchases_count",
        "created_at",
    )
    list_filter = ("type", "is_deleted", "starts_at")
    search_fields = ("title", "slug", "sub_title")
    readonly_fields = ("course_id", "created_at", "updated_at", "image_preview", "slug")
    ordering = ("-created_at",)
    list_per_page = 20
    inlines = [SectionInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "course_id",
                    "title",
                    "sub_title",
                    "slug",
                    "description",
                    "authors",
                ),
            },
        ),
        (
            "Изображение",
            {
                "fields": ("image", "image_preview"),
            },
        ),
        (
            "Настройки",
            {
                "fields": (
                    "type",
                    "price",
                    "is_deleted",
                    "starts_at",
                    "duration_weeks",
                    "min_age",
                ),
            },
        ),
        (
            "Интеграции",
            {
                "fields": ("kinescope_folder_id", "yandex_vs_id"),
                "classes": ["collapse"],
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

    @display(description="")
    def image_thumb(self, obj):
        url = obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="height:36px;width:54px;object-fit:cover;border-radius:4px;" />',
                url,
            )
        return ""

    @display(description="Название")
    def title_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.pk])
        deleted = " 🗑" if obj.is_deleted else ""
        return format_html('<a href="{}">{}{}</a>', url, obj.title, deleted)

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        if obj.is_deleted:
            return "Удалён", "red"
        colors = {"published": "green", "draft": "yellow"}
        return obj.get_type_display().capitalize(), colors.get(obj.type, "gray")

    @display(description="Цена")
    def price_display(self, obj):
        return f"{obj.price:,} ₽"

    @display(description="Авторы")
    def authors_list(self, obj):
        names = []
        for a in obj.authors.all()[:3]:
            full = f"{a.first_name} {a.last_name}".strip() or str(a)
            names.append(full)
        return ", ".join(names) or "—"

    @display(description="Покупок")
    def purchases_count(self, obj):
        return obj.enrollments.count()

    @display(description="Превью")
    def image_preview(self, obj):
        url = obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="max-height:160px;border-radius:8px;" />',
                url,
            )
        return "—"


@admin.register(Section)
class SectionAdmin(ModelAdmin):
    list_display = ("section_number", "title", "course_link", "status_badge", "created_at")
    list_filter = ("type", "course")
    search_fields = ("title", "course__title")
    readonly_fields = ("section_id", "section_number", "created_at", "updated_at", "slug")
    ordering = ("course", "section_number")
    inlines = [LessonInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": ("section_id", "course", "section_number", "title", "slug", "type"),
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

    @display(description="Курс")
    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {"published": "green", "draft": "yellow"}
        return obj.get_type_display().capitalize(), colors.get(obj.type, "gray")


@admin.register(Lesson)
class LessonAdmin(ModelAdmin):
    list_display = ("lesson_number", "title", "section_link", "status_badge", "created_at")
    list_filter = ("type", "section__course")
    search_fields = ("title", "section__title", "section__course__title")
    readonly_fields = ("lesson_id", "lesson_number", "created_at", "updated_at", "slug")
    ordering = ("section", "lesson_number")
    inlines = [HomeworkInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": ("lesson_id", "section", "lesson_number", "title", "slug", "type"),
            },
        ),
        (
            "Контент",
            {
                "fields": ("document",),
                "classes": ["collapse"],
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

    @display(description="Секция")
    def section_link(self, obj):
        if obj.section:
            url = reverse("admin:courses_section_change", args=[obj.section_id])
            return format_html('<a href="{}">{}</a>', url, obj.section.title)
        return "—"

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {"published": "green", "draft": "yellow"}
        return obj.get_type_display().capitalize(), colors.get(obj.type, "gray")


@admin.register(Homework)
class HomeworkAdmin(ModelAdmin):
    list_display = (
        "homework_number",
        "title",
        "lesson_link",
        "deadline_display",
        "max_points",
        "attempts_count",
        "created_at",
    )
    list_filter = ("type", "deadline")
    search_fields = ("title", "lesson__title", "lesson__section__course__title")
    readonly_fields = (
        "homework_id",
        "homework_number",
        "created_at",
        "updated_at",
        "slug",
        "max_points",
    )
    ordering = ("lesson", "homework_number")
    inlines = [QuestionInline, TaskInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "homework_id",
                    "lesson",
                    "homework_number",
                    "title",
                    "slug",
                    "type",
                    "deadline",
                    "max_points",
                ),
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

    @display(description="Урок")
    def lesson_link(self, obj):
        url = reverse("admin:courses_lesson_change", args=[obj.lesson_id])
        return format_html('<a href="{}">{}</a>', url, obj.lesson.title)

    @display(description="Дедлайн")
    def deadline_display(self, obj):
        if timezone.now() > obj.deadline:
            return format_html(
                '<span style="color:#ef4444;">{}</span>', obj.deadline.strftime("%d.%m.%Y %H:%M")
            )
        return obj.deadline.strftime("%d.%m.%Y %H:%M")

    @display(description="Попыток")
    def attempts_count(self, obj):
        return obj.attempt_set.count()


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ("question_number", "text", "homework_link", "correct_ans", "max_points")
    search_fields = ("text", "homework__title")
    readonly_fields = ("question_id", "question_number", "created_at", "updated_at")
    ordering = ("homework", "question_number")

    @display(description="Домашнее задание")
    def homework_link(self, obj):
        url = reverse("admin:courses_homework_change", args=[obj.homework_id])
        return format_html('<a href="{}">{}</a>', url, obj.homework.title)


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ("task_number", "text", "homework_link", "max_points")
    search_fields = ("text", "homework__title")
    readonly_fields = ("task_id", "task_number", "created_at", "updated_at")
    ordering = ("homework", "task_number")

    @display(description="Домашнее задание")
    def homework_link(self, obj):
        url = reverse("admin:courses_homework_change", args=[obj.homework_id])
        return format_html('<a href="{}">{}</a>', url, obj.homework.title)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(ModelAdmin):
    list_display = (
        "user_link",
        "course_link",
        "source",
        "payment_link",
        "access_expires_at",
        "is_active_badge",
    )
    list_filter = ("source", "access_expires_at", "course")
    search_fields = ("user__email_cipher", "user__first_name", "course__title")
    readonly_fields = ("user", "course", "payment", "source", "access_expires_at", "created_at")

    @display(description="Пользователь")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    @display(description="Курс")
    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @display(description="Платёж")
    def payment_link(self, obj):
        if not obj.payment_id:
            return "—"
        url = reverse("admin:payments_payment_change", args=[obj.payment_id])
        return format_html('<a href="{}">#{}</a>', url, obj.payment_id)

    @display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active
