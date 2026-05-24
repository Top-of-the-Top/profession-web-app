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

        vs_files = course.prepare_files_for_vs()

        temp_paths = []
        for filename, content in vs_files:
            suffix = os.path.splitext(filename)[1] or ".txt"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, mode="w", encoding="utf-8"
            ) as tf:
                tf.write(content)
                temp_paths.append(tf.name)

        try:
            asyncio.run(service.update_course_context(course, temp_paths))
            logger.info(f"Successfully synced knowledge base for course: {course.title}")

        finally:
            for path in temp_paths:
                if os.path.exists(path):
                    os.remove(path)

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
