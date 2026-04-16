import tempfile
import logging 
import os
import asyncio
from celery import shared_task
from apps.courses.models import Course
from apps.ai_chat_bot.services import YandexKnowledgeAIService # Твой сервис

logger = logging.getLogger(__name__)

@shared_task(name="synchronize_course_context")
def synchronize_course_context(course_id):
    try:
        course = Course.objects.get(id=course_id)
        service = YandexKnowledgeAIService()
        
        full_text = course.prepare_full_content_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tf:
            tf.write(full_text)
            temp_path = tf.name

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                service.update_course_context(course, [temp_path])
            )
            logger.info(f"Successfully synced knowledge base for course: {course.title}")
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Course.DoesNotExist:
        logger.error(f"Course with id {course_id} not found")
    except Exception as e:
        logger.error(f"Error syncing course {course_id}: {e}")
        