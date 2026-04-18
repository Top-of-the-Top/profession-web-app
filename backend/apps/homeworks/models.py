import uuid
from enum import Enum 
from django.core.exceptions import ValidationError
from django.db import models
from apps.users.models import User
from apps.courses.models import Homework, Task, Question


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Attempt(TimestampedMixin):
    DRAFT_STATUS = 'draft'
    SUBMITTED_STATUS = 'submitted'
    REVIEWED_STATUS = 'reviewed'

    STATUS_CHOICES = [
        (DRAFT_STATUS, 'Черновик'),
        (SUBMITTED_STATUS, 'Отправлено'),
        (REVIEWED_STATUS, 'Оценено'),
    ]

    attempt_id = models.UUIDField(primary_key=True, verbose_name='id', default=uuid.uuid4)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT_STATUS,
        verbose_name='Статус',
    )
    send_at = models.DateTimeField(null=True, blank=True, verbose_name='Время отправки')
    grade = models.PositiveIntegerField(
        null=True, blank=True, default=None, verbose_name='Количество баллов'
    )

    class Meta:
        verbose_name = 'Попытка'
        verbose_name_plural = 'Попытки'
        ordering = ['created_at']
        unique_together = ('user', 'homework')
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return str(self.attempt_id)


class EstimatedMixin(models.Model):
    CORRECT_STATUS = 'correct'
    INCORRECT_STATUS = 'incorrect'
    PARTIAL_STATUS = 'partily'

    STATUS_CHOICES = [
        (CORRECT_STATUS, 'Верно'),
        (INCORRECT_STATUS, 'Неверно'),
        (PARTIAL_STATUS, 'Частично верно'),
    ]

    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=STATUS_CHOICES,
        verbose_name='Статус',
    )

    class Meta:
        abstract = True


class QuestionAnswer(EstimatedMixin, TimestampedMixin):
    answer_id = models.UUIDField(primary_key=True, verbose_name='id', default=uuid.uuid4)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name='question_answers',
    )

    user_answer = models.CharField(
        max_length=120, blank=True, default='', verbose_name='Ответ пользователя'
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Ответ на вопрос'
        verbose_name_plural = 'Ответы на вопросы'
        ordering = ['-created_at']
        unique_together = ('attempt', 'question')

    def clean(self):
        if self.user_answer and self.user_answer not in self.question.answer_options:
            raise ValidationError({
                'user_answer': f'Answer must be one of: {", ".join(self.question.answer_options)}'
            })

    def __str__(self):
        return str(self.answer_id)


class TaskAnswer(EstimatedMixin, TimestampedMixin):
    answer_id = models.UUIDField(primary_key=True, verbose_name='id', default=uuid.uuid4)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name='task_answers',
    )

    user_answer = models.TextField(blank=True, default='', verbose_name='Ответ пользователя')
    points = models.PositiveIntegerField(
        null=True, blank=True, default=None, verbose_name='Баллы за задание'
    )
    teacher_comment = models.TextField(
        blank=True, default='', verbose_name='Комментарий преподавателя'
    )

    class Meta:
        verbose_name = 'Ответ на задание'
        verbose_name_plural = 'Ответы на задания'
        ordering = ['created_at']
        unique_together = ('attempt', 'task')

    def clean(self):
        if self.points is not None and self.points > self.task.max_points:
            raise ValidationError({
                'points': f'За задание {self.task} можно получить максимум {self.task.max_points}'
            })

    def __str__(self):
        return str(self.answer_id)
    