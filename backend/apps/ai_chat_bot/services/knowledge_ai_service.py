import logging
import os
import asyncio
from apps.courses.models import Course
from asgiref.sync import sync_to_async
from apps.ai_chat_bot.services.base_service import YandexAIBase

logger = logging.getLogger(__name__)


class YandexKnowledgeAIService(YandexAIBase):
    
    async def update_course_context(self, course, file_paths):
        logger.info(f"Starting huge context update for course {course.title}")
        
        old_vs_id = course.yandex_vs_id
        new_vs_id = None

        try:
            new_file_ids = await asyncio.gather(*[self._upload_file(p) for p in file_paths])      
            
            new_vs = await self.client.beta.vector_stores.create(
                name=f"База знаний для курса {course.title}",
                file_ids=[f.id for f in new_file_ids]
            )
            new_vs_id = new_vs.id

            await self._wait_for_vector_store(new_vs_id)

            await sync_to_async(Course.objects.filter(pk=course.pk).update)(yandex_vs_id=new_vs_id)
            course.yandex_vs_id = new_vs_id

            if old_vs_id:
                asyncio.create_task(self._delete_vector_store_by_id(old_vs_id, course.pk))

        except Exception as e:
            logger.error(f"Error during context update for {course.pk}: {e}")
            if new_vs_id:
                await self._delete_vector_store_by_id(new_vs_id, course.pk)
            raise

    async def _upload_file(self, file_path):
        async with self._semaphore:
            logger.info(f"Uploading file {os.path.basename(file_path)}")
            try:
                with open(file_path, "rb") as f:
                    return await self.client.files.create(
                        file=f, 
                        purpose="assistants"
                    )
            except Exception as e:
                logger.error(f"Failed to upload file {file_path}: {e}")
                raise

    async def _wait_for_vector_store(self, vs_id, interval=3):
        logger.info(f"Starting poll for VS: {vs_id}")
        while True:
            vs = await self.client.beta.vector_stores.retrieve(vs_id)
            if vs.status == "completed":
                logger.info(f"Vector Store {vs_id} is READY")
                return vs 
            if vs.status == "failed":
                logger.error(f"Vector Store {vs_id} FAILED. Error: {getattr(vs, 'last_error', 'Unknown')}")
                raise Exception(f"Vector Store {vs_id} creation failed")
            
            await asyncio.sleep(interval)

    async def _delete_vector_store_by_id(self, vs_id, course_id):
        try:
            logger.info(f"Starting full cleanup for Vector Store for course {course_id}")

            vs_files = await self.client.beta.vector_stores.files.list(vector_store_id=vs_id)
            file_ids = [f.id for f in vs_files.data]

            logger.info(f"Deleting Vector Store")
            await self.client.beta.vector_stores.delete(vs_id)

            async def delete_file(f_id):
                async with self._semaphore:
                    try:
                        await self.client.files.delete(f_id)
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to delete file {f_id}: {e}")
                        return False

            deleted = await asyncio.gather(*(delete_file(f_id) for f_id in file_ids))
            success_count = sum(1 for i in deleted if i)
            logger.info(f"Cleanup finished. Deleted VS {vs_id} and {success_count}/{len(file_ids)} files")

        except Exception as e:
            logger.error(f"Critical error during VS deletion {vs_id}: {e}")
            raise