from django.db import models
from django.db.models.signals import pre_delete, pre_save
import os
from django.dispatch import receiver

DEFAULT_COURSE_IMAGE = "courses/default_course.png"


def course_image_path(instance, filename):
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


class Homework(models.Model):
    homework_id = models.AutoField(primary_key=True)
    lesson_id = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)

    def __str__(self):
        return self.title