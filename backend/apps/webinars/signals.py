from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.courses.api.utils.cache_utils import (
    invalidate_lesson_detail_cache,
    invalidate_schedule_cache,
)
from apps.webinars.models import Recording, Webinar


@receiver([post_save, post_delete], sender=Webinar)
def invalidate_lesson_cache_on_webinar_change(sender, instance, **kwargs):
    lesson = instance.lesson
    if lesson is None:
        return
    section = lesson.section
    if section is None:
        return
    invalidate_lesson_detail_cache(section.course.slug, lesson.slug)
    invalidate_schedule_cache()


@receiver([post_save, post_delete], sender=Recording)
def invalidate_lesson_cache_on_recording_change(sender, instance, **kwargs):
    webinar = instance.webinar
    if webinar is None:
        return
    lesson = webinar.lesson
    if lesson is None:
        return
    section = lesson.section
    if section is None:
        return
    invalidate_lesson_detail_cache(section.course.slug, lesson.slug)
