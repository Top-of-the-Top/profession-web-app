from django.db import models

class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=120, verbose_name = 'Название курса')
    slug = models.SlugField(max_length=120, verbose_name = 'URL', blank=True)
    price = models.PositiveIntegerField()


class Lesson(models.Model):
    lesson_id = models.AutoField(primary_key=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    date = models.DateTimeField()


class Homework(models.Model):
    homework_id = models.AutoField(primary_key=True)
    lesson_id = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)