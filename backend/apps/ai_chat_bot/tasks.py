import asyncio
import logging

from celery import shared_task

from apps.ai_chat_bot.services.knowledge_ai_service import YandexKnowledgeAIService
from apps.courses.models import Course

logger = logging.getLogger(__name__)


@shared_task(name="synchronize_course_context")
def synchronize_course_context(course_id):
    try:
        course = Course.objects.get(pk=course_id)
        service = YandexKnowledgeAIService()
        files = course.prepare_files_for_vs()
        asyncio.run(service.update_course_context(course, files))
        logger.info("Successfully synced VS for course: %s", course.title)
    except Course.DoesNotExist:
        logger.error("Course %s not found", course_id)
    except Exception as e:
        logger.error("Error syncing course %s: %s", course_id, e)


@shared_task(name="rebuild_all_courses_vs")
def rebuild_all_courses_vs():
    courses = Course.objects.filter(
        is_deleted=False,
        section__isnull=False,
    ).distinct()

    for course in courses:
        try:
            synchronize_course_context.delay(course.pk)
            logger.info("Queued VS rebuild for course: %s (id=%s)", course.title, course.pk)
        except Exception as e:
            logger.error("Failed to queue VS rebuild for course %s: %s", course.pk, e)
