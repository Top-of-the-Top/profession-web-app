import uuid

from django.db import models

from apps.courses.models import Homework, Question, Task
from apps.users.models import User


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Attempt(TimestampedMixin):
    DRAFT_STATUS = "draft"
    SUBMITTED_STATUS = "submitted"
    REVIEWED_STATUS = "reviewed"

    STATUS_CHOICES = [
        (DRAFT_STATUS, "Черновик"),
        (SUBMITTED_STATUS, "Отправлено"),
        (REVIEWED_STATUS, "Оценено"),
    ]

    attempt_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT_STATUS,
        verbose_name="Статус",
    )
    send_at = models.DateTimeField(null=True, blank=True, verbose_name="Время отправки")
    grade = models.PositiveIntegerField(
        null=True, blank=True, default=None, verbose_name="Количество баллов"
    )

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_attempts",
        verbose_name="Кто проверил",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Когда проверено",
    )

    class Meta:
        verbose_name = "Попытка"
        verbose_name_plural = "Попытки"
        ordering = ["created_at"]
        unique_together = ("user", "homework")
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return str(self.attempt_id)


class EstimatedMixin(models.Model):
    CORRECT_STATUS = "correct"
    INCORRECT_STATUS = "incorrect"
    PARTIAL_STATUS = "partily"

    STATUS_CHOICES = [
        (CORRECT_STATUS, "Верно"),
        (INCORRECT_STATUS, "Неверно"),
        (PARTIAL_STATUS, "Частично верно"),
    ]

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=STATUS_CHOICES,
        verbose_name="Статус",
    )

    class Meta:
        abstract = True


class QuestionAnswer(EstimatedMixin, TimestampedMixin):
    answer_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="question_answers",
    )

    user_answer = models.CharField(
        max_length=120, blank=True, default="", verbose_name="Ответ пользователя"
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"
        ordering = ["-created_at"]
        unique_together = ("attempt", "question")

    def __str__(self):
        return str(self.answer_id)


class TaskAnswer(EstimatedMixin, TimestampedMixin):
    answer_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="task_answers",
    )

    user_answer = models.TextField(blank=True, default="", verbose_name="Ответ пользователя")

    class Meta:
        verbose_name = "Ответ на задание"
        verbose_name_plural = "Ответы на задания"
        ordering = ["created_at"]
        unique_together = ("attempt", "task")

    def __str__(self):
        return str(self.answer_id)


class TaskReview(TimestampedMixin):
    task_review_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    answer = models.OneToOneField(
        TaskAnswer,
        on_delete=models.CASCADE,
        related_name="review",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="task_reviews",
        verbose_name="Проверяющий",
    )

    comment = models.TextField(
        max_length=1500,
        verbose_name="Комментарий преподавателя",
        null=True,
        blank=True,
        default=None,
    )
    points = models.PositiveIntegerField(verbose_name="Выставленные баллы", default=0)

    class Meta:
        verbose_name = "Ревью задания с развернутым ответом"
        verbose_name_plural = "Ревью заданий с развернутым ответом"
        ordering = ["-created_at"]
