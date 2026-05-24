import asyncio
import logging

from asgiref.sync import sync_to_async

from apps.ai_chat_bot.services.base_service import YandexAIBase
from apps.courses.models import Course

logger = logging.getLogger(__name__)


class YandexKnowledgeAIService(YandexAIBase):
    async def update_course_context(self, course, files: list[tuple[str, str]]) -> None:
        old_vs_id = course.yandex_vs_id or None
        new_vs_id = None
        uploaded_file_ids: list[str] = []

        try:
            upload_results = await asyncio.gather(
                *[self._upload_named_file(name, content) for name, content in files]
            )
            uploaded_file_ids = [r.id for r in upload_results]
            logger.info("Uploaded %d files for course %s", len(uploaded_file_ids), course.pk)

            new_vs = await self.client.vector_stores.create(
                name=f"course-{course.pk}",
                file_ids=uploaded_file_ids,
            )
            new_vs_id = new_vs.id
            logger.info("Created VS %s for course %s", new_vs_id, course.pk)

            await self._wait_for_vector_store(new_vs_id)

            await sync_to_async(Course.objects.filter(pk=course.pk).update)(yandex_vs_id=new_vs_id)
            logger.info("Saved VS %s to course %s", new_vs_id, course.pk)

            if old_vs_id:
                await self._delete_vs_and_files(old_vs_id)

        except Exception as e:
            logger.error("VS sync failed for course %s: %s", course.pk, e)
            if new_vs_id:
                await self._safe_cleanup_vs(new_vs_id, uploaded_file_ids)
            elif uploaded_file_ids:
                await asyncio.gather(
                    *[self._safe_delete_file(fid) for fid in uploaded_file_ids],
                    return_exceptions=True,
                )
            raise

    async def _upload_named_file(self, name: str, content: str):
        async with self._semaphore:
            logger.info("Uploading %s", name)
            try:
                return await self.client.files.create(
                    file=(name, content.encode("utf-8"), "text/plain"),
                    purpose="assistants",
                )
            except Exception as e:
                logger.error("Failed to upload %s: %s", name, e)
                raise

    async def _wait_for_vector_store(self, vs_id: str, interval: int = 3, timeout: int = 300) -> None:
        logger.info("Polling VS %s until ready", vs_id)
        elapsed = 0
        while True:
            vs = await self.client.vector_stores.retrieve(vs_id)
            if vs.status == "completed":
                logger.info("VS %s is READY", vs_id)
                return
            if vs.status == "failed":
                raise RuntimeError(f"Vector Store {vs_id} failed: {getattr(vs, 'last_error', 'unknown')}")
            if elapsed >= timeout:
                raise TimeoutError(f"Vector Store {vs_id} did not become ready in {timeout}s")
            await asyncio.sleep(interval)
            elapsed += interval

    async def _delete_vs_and_files(self, vs_id: str) -> None:
        try:
            vs_files = await self.client.vector_stores.files.list(vector_store_id=vs_id)
            file_ids = [f.id for f in vs_files.data]
            await self.client.vector_stores.delete(vs_id)
            await asyncio.gather(
                *[self._safe_delete_file(fid) for fid in file_ids],
                return_exceptions=True,
            )
            logger.info("Deleted VS %s and %d files", vs_id, len(file_ids))
        except Exception as e:
            logger.warning("Failed to fully delete VS %s: %s", vs_id, e)

    async def _safe_cleanup_vs(self, vs_id: str, file_ids: list[str]) -> None:
        await asyncio.gather(
            self._safe_delete_vs(vs_id),
            *[self._safe_delete_file(fid) for fid in file_ids],
            return_exceptions=True,
        )

    async def _safe_delete_vs(self, vs_id: str) -> None:
        try:
            await self.client.vector_stores.delete(vs_id)
        except Exception as e:
            logger.warning("Failed to delete VS %s: %s", vs_id, e)

    async def _safe_delete_file(self, file_id: str) -> None:
        try:
            await self.client.files.delete(file_id)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", file_id, e)
