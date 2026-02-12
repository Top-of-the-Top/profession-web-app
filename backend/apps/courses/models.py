from django.db import models
from django.db.models.signals import pre_delete, pre_save
import os
from django.dispatch import receiver
from rest_framework.exceptions import ValidationError
from ..users.models import User
from django.db.models import Sum

DEFAULT_COURSE_IMAGE = "courses/default_course.png"


def course_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f'courses/course_{instance.pk}.{ext}'


class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, verbose_name='Название курса')
    sub_title = models.CharField(max_length=200, verbose_name='Краткое описание курса')
    description = models.TextField(verbose_name = "Описание курса")
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    price = models.PositiveIntegerField()
    image = models.ImageField(
        upload_to=course_image_path,
        blank=True,
        null=True,
        verbose_name='Изображение курса',
        default=DEFAULT_COURSE_IMAGE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def image_url(self):
        if self.image and self.image.name != DEFAULT_COURSE_IMAGE:
            return self.image.url
        bucket = os.getenv("AWS_S3_BUCKET_NAME", "your-bucket")
        return f'https://storage.yandexcloud.net/{bucket}/{DEFAULT_COURSE_IMAGE}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if is_new and self.image and hasattr(self.image, 'file') and self.image.name != DEFAULT_COURSE_IMAGE:
            image_file = self.image.file
            original_name = getattr(self.image, 'name', 'image.jpg')
            
            self.image = None
            super().save(*args, **kwargs)
            
            ext = original_name.split('.')[-1].lower() if '.' in original_name else 'jpg'
            new_name = f'courses/course_{self.pk}.{ext}'
            
            image_file.seek(0)
            self.image.save(new_name, image_file, save=False)
            super().save(update_fields=['image'])
        else:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
@receiver(pre_save, sender=Course)
def handle_course_image_update(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if (old_instance.image and old_instance.image.name != DEFAULT_COURSE_IMAGE and
                instance.image and instance.image != old_instance.image):
            old_instance.image.delete(save=False)
    except sender.DoesNotExist:
        pass


@receiver(pre_delete, sender=Course)
def delete_course_image(sender, instance, **kwargs):
    if instance.image and instance.image.name != DEFAULT_COURSE_IMAGE:
        instance.image.delete(save=False)



class Lesson(models.Model):
    lesson_id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    date = models.DateTimeField()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['date']


class Homework(models.Model):
    homework_id = models.AutoField(primary_key=True)
    lesson_id = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Домашнее задание'
        verbose_name_plural = 'Домашние задания'
        ordering = ['created_at']

    def __str__(self):
        return self.title

class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    homework_id = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200) # Пока работаем только с текстовыми вопросами. Без картинок и так далее
    correct_ans = models.CharField() # Пока считаем, что всего может быть только 1 правильный ответ
    answer_options = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['homework_id'])
        ]

    def __str__(self):
        return self.description

class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    homework_id = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    max_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['homework_id'])
        ]

    def __str__(self):
        return self.question

class Users_Homeworks_Attempts(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ]

    attempt_id = models.AutoField(primary_key=True)
    homework_id = models.ForeignKey(Homework, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    send_at = models.DateTimeField(null=True, blank=True)

    @property
    def grade(self):
        if self.status != 'reviewed':
            return None

        task_points = self.task_answers.filter(
            task_status='reviewed'
        ).aggregate(points=Sum('points'))['points'] or 0

        question_points = self.question_answers.filter(
            is_correct=True
        ).count()

        task_max = self.homework_id.task_set.aggregate(
            total=Sum('max_points')
        )['total'] or 0

        question_max = self.homework_id.question_set.count()

        total_max = task_max + question_max
        total_points = task_points + question_points

        percentage: float = (total_points / (total_max * 100.0)) if total_max > 0 else 0

        return max(1, min(10, round(percentage / 10)))

    class Meta:
        verbose_name = 'Попытка'
        verbose_name_plural = 'Попытки'
        ordering = ['created_at']
        unique_together = ('homework_id', 'user_id') # Уникальная пара ключей, при submit просто обновляем через PUT/PATCH
        indexes = [
            models.Index(fields=['user_id', 'homework_id', 'status'])
        ]

    def __str__(self):
        return self.attempt_id


class Users_questions_answers(models.Model):
    answer_id = models.AutoField(primary_key=True)
    question_id = models.ForeignKey(Question, on_delete=models.CASCADE)
    attempt_id = models.ForeignKey(Users_Homeworks_Attempts, on_delete=models.CASCADE, related_name='question_answers')

    is_correct = models.BooleanField(default=False)
    user_answer = models.CharField(max_length=120)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ответ на вопрос'
        verbose_name_plural = 'Ответы на вопросы'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['attempt_id', 'question_id'])
        ]

    def __str__(self):
        return self.answer_id

class Users_tasks_answers(models.Model):
    TASK_STATUS_CHOICES = [
        # Начали отвечать -> draft -> отправили всю домашку -> submitted -> эту проверили -> reviewed
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ]
    answer_id = models.AutoField(primary_key=True)

    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)
    attempt_id = models.ForeignKey(Users_Homeworks_Attempts, on_delete=models.CASCADE, related_name='task_answers')

    points = models.PositiveIntegerField(default=0) # Как то проверять, что не больше чем max_points у соответствующего вопроса

    user_answer = models.TextField() # Пока не понятно, что загружаем в качестве ответа. Пока будет Text без ограничений.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    task_status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='submitted')

    def clean(self):
        if self.points > self.task_id.max_points: # Проверяем что выставлено корректное количество баллов
            raise ValidationError({
                'points' : f'За задание {self.task_id} можно получить максимум {self.task_id.max_points}'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.answer_id

    class Meta:
        verbose_name = 'Ответ на задание'
        verbose_name_plural = 'Ответы на задания'
        ordering = ['created_at']

        indexes = [
            models.Index(fields=['attempt_id', 'task_id', 'task_status'])
        ]