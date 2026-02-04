from django.db import models
from uuid import uuid4

from django.dispatch import receiver

DEFAULT_COURSE_IMAGE = "courses/default_course.png"
def course_image_path(instance, filename):
    """Сохраняет изображение как course_<id>.jpg"""
    ext = filename.split('.')[-1].lower()
    return f'courses/course_{instance.pk}.{ext}'


class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=120, verbose_name='Название курса')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    price = models.PositiveIntegerField()
    image = models.ImageField(
        upload_to=course_image_path,
        blank=True,
        null=True,
        verbose_name='Изображение курса',
        default=DEFAULT_COURSE_IMAGE,
    )

    def save(self, *args, **kwargs):
        super(Course, self).save(*args, **kwargs)

        if self.image:
            new_name = course_image_path(self,self.image.name)
            self.image.name = new_name
            super().save(update_fields=['image'])


    def __str__(self):
        return self.title


class Lesson(models.Model):
    lesson_id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    date = models.DateTimeField()

    def __str__(self):
        return self.title


class Homework(models.Model):
    homework_id = models.AutoField(primary_key=True)
    lesson_id = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)

    def __str__(self):
        return self.title