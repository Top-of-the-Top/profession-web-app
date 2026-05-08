from django.core.cache import caches
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.homeworks.models import Attempt
from apps.stats.models import LessonProgress, RecordingView, WebinarAttendance
from apps.stats.tasks import recompute_lesson_progress_task


@receiver(post_save, sender=WebinarAttendance)
def on_webinar_attendance_change(sender, instance, **kwargs):
    lesson = instance.webinar.lesson
    recompute_lesson_progress_task.delay(instance.user_id, lesson.pk)


@receiver(post_save, sender=RecordingView)
def on_recording_view_change(sender, instance, **kwargs):
    lesson = instance.recording.webinar.lesson
    recompute_lesson_progress_task.delay(instance.user_id, lesson.pk)


@receiver(post_save, sender=Attempt)
def on_attempt_change(sender, instance, **kwargs):
    lesson = instance.homework.lesson
    recompute_lesson_progress_task.delay(instance.user_id, lesson.pk)


@receiver([post_save, post_delete], sender=LessonProgress)
def invalidate_aggregate_cache_on_progress_change(sender, instance, **kwargs):
    cache = caches["default"]
    course = instance.lesson.section.course
    cache.delete(f"default:stats:course_meta:staff:{course.slug}")
    cache.delete(f"default:stats:lesson_meta:staff:{instance.lesson.slug}")
