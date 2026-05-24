import asyncio
import logging
import os
import tempfile

from celery import shared_task

from apps.ai_chat_bot.services.knowledge_ai_service import YandexKnowledgeAIService
from apps.courses.models import Course

logger = logging.getLogger(__name__)


@shared_task(name="synchronize_course_context")
def synchronize_course_context(course_id):
    try:
        course = Course.objects.get(pk=course_id)
        service = YandexKnowledgeAIService()

        full_text = course.prepare_full_content_file()

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt", mode="w", encoding="utf-8"
        ) as tf:
            tf.write(full_text)
            temp_path = tf.name

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(service.update_course_context(course, [temp_path]))
            logger.info(f"Successfully synced knowledge base for course: {course.title}")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Course.DoesNotExist:
        logger.error(f"Course with id {course_id} not found")
    except Exception as e:
        logger.error(f"Error syncing course {course_id}: {e}")


@shared_task(name="rebuild_all_courses_vs")
def rebuild_all_courses_vs():
    courses = Course.objects.filter(
        is_deleted=False,
        section__isnull=False,
    ).distinct()

    for course in courses:
        try:
            synchronize_course_context.delay(course.pk)
            logger.info(f"Queued VS rebuild for course: {course.title} (id={course.pk})")
        except Exception as e:
            logger.error(f"Failed to queue VS rebuild for course {course.pk}: {e}")
