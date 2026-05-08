import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="statistics.recompute_lesson_progress")
def recompute_lesson_progress_task(user_id, lesson_id):
    from apps.courses.models import Lesson
    from apps.stats.services.progress_service import recompute_lesson_progress
    from apps.users.models import User

    try:
        user = User.objects.get(pk=user_id)
        lesson = Lesson.objects.get(pk=lesson_id)
    except (User.DoesNotExist, Lesson.DoesNotExist):
        logger.warning(
            "Не найден user=%s или lesson=%s для пересчёта прогресса", user_id, lesson_id
        )
        return

    recompute_lesson_progress(user=user, lesson=lesson)
