from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Attempt, QuestionAnswer, TaskAnswer, TaskReview


class QuestionAnswerInline(TabularInline):
    model = QuestionAnswer
    extra = 0
    readonly_fields = ("question", "user_answer", "is_correct", "status", "created_at")
    fields = ("question", "user_answer", "is_correct", "status")
    can_delete = False


class TaskAnswerInline(TabularInline):
    model = TaskAnswer
    extra = 0
    readonly_fields = ("task", "user_answer", "status", "created_at")
    fields = ("task", "user_answer", "status")
    can_delete = False
    show_change_link = True


@admin.register(Attempt)
class AttemptAdmin(ModelAdmin):
    list_display = (
        "attempt_short_id",
        "user_link",
        "homework_link",
        "status_badge",
        "grade_display",
        "reviewed_by_link",
        "send_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "user__email_cipher",
        "user__first_name",
        "homework__title",
    )
    readonly_fields = ("attempt_id", "created_at", "updated_at", "send_at", "reviewed_at")
    ordering = ("-created_at",)
    inlines = [QuestionAnswerInline, TaskAnswerInline]

    fieldsets = (
        (
            "Попытка",
            {
                "fields": ("attempt_id", "user", "homework", "status", "send_at"),
            },
        ),
        (
            "Оценка",
            {
                "fields": ("grade", "reviewed_by", "reviewed_at"),
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
    def attempt_short_id(self, obj):
        return str(obj.attempt_id)[:8] + "…"

    @display(description="Студент")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip() or str(obj.user)
        return format_html('<a href="{}">{}</a>', url, name)

    @display(description="Домашнее задание")
    def homework_link(self, obj):
        url = reverse("admin:courses_homework_change", args=[obj.homework_id])
        return format_html('<a href="{}">{}</a>', url, obj.homework.title)

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "draft": "gray",
            "submitted": "yellow",
            "reviewed": "green",
        }
        return obj.get_status_display(), colors.get(obj.status, "gray")

    @display(description="Оценка")
    def grade_display(self, obj):
        if obj.grade is not None:
            max_pts = obj.homework.max_points
            return f"{obj.grade} / {max_pts}"
        return "—"

    @display(description="Проверил")
    def reviewed_by_link(self, obj):
        if obj.reviewed_by:
            url = reverse("admin:users_user_change", args=[obj.reviewed_by_id])
            name = f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip() or str(
                obj.reviewed_by
            )
            return format_html('<a href="{}">{}</a>', url, name)
        return "—"


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(ModelAdmin):
    list_display = (
        "answer_short_id",
        "attempt_link",
        "question",
        "user_answer",
        "is_correct",
        "status_badge",
    )
    list_filter = ("is_correct", "status")
    search_fields = ("attempt__user__email_cipher", "question__text")
    readonly_fields = ("answer_id", "created_at", "updated_at", "attempt", "question")

    @display(description="ID")
    def answer_short_id(self, obj):
        return str(obj.answer_id)[:8] + "…"

    @display(description="Попытка")
    def attempt_link(self, obj):
        url = reverse("admin:homeworks_attempt_change", args=[obj.attempt_id])
        return format_html('<a href="{}">…{}</a>', url, str(obj.attempt_id)[:8])

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "correct": "green",
            "incorrect": "red",
            "partily": "yellow",
        }
        label = obj.get_status_display() if obj.status else "Не оценено"
        return label, colors.get(obj.status or "", "gray")


class TaskReviewInline(TabularInline):
    model = TaskReview
    extra = 0
    readonly_fields = ("reviewer", "points", "comment", "created_at")
    fields = ("reviewer", "points", "comment")
    can_delete = False


@admin.register(TaskAnswer)
class TaskAnswerAdmin(ModelAdmin):
    list_display = ("answer_short_id", "attempt_link", "task", "status_badge", "has_review")
    list_filter = ("status",)
    search_fields = ("attempt__user__email_cipher", "task__text")
    readonly_fields = ("answer_id", "created_at", "updated_at", "attempt", "task")
    inlines = [TaskReviewInline]

    @display(description="ID")
    def answer_short_id(self, obj):
        return str(obj.answer_id)[:8] + "…"

    @display(description="Попытка")
    def attempt_link(self, obj):
        url = reverse("admin:homeworks_attempt_change", args=[obj.attempt_id])
        return format_html('<a href="{}">…{}</a>', url, str(obj.attempt_id)[:8])

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "correct": "green",
            "incorrect": "red",
            "partily": "yellow",
        }
        label = obj.get_status_display() if obj.status else "Без оценки"
        return label, colors.get(obj.status or "", "gray")

    @display(description="Ревью", boolean=True)
    def has_review(self, obj):
        return hasattr(obj, "review")


@admin.register(TaskReview)
class TaskReviewAdmin(ModelAdmin):
    list_display = ("task_review_short_id", "answer_link", "reviewer_link", "points", "created_at")
    search_fields = ("reviewer__email_cipher", "answer__task__text")
    readonly_fields = ("task_review_id", "created_at", "updated_at", "answer")

    @display(description="ID")
    def task_review_short_id(self, obj):
        return str(obj.task_review_id)[:8] + "…"

    @display(description="Ответ")
    def answer_link(self, obj):
        url = reverse("admin:homeworks_taskanswer_change", args=[obj.answer_id])
        return format_html('<a href="{}">…{}</a>', url, str(obj.answer_id)[:8])

    @display(description="Проверяющий")
    def reviewer_link(self, obj):
        if obj.reviewer:
            url = reverse("admin:users_user_change", args=[obj.reviewer_id])
            name = f"{obj.reviewer.first_name} {obj.reviewer.last_name}".strip() or str(
                obj.reviewer
            )
            return format_html('<a href="{}">{}</a>', url, name)
        return "—"
