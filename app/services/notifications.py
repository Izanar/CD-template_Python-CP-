import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config.config import create_application_config
from app.repository.database.base import DatabaseRepository
from app.schemas.enums.notification_status import NotificationStatus

config = create_application_config()

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db_repo: DatabaseRepository):
        self.db_repo = db_repo

    async def _send_notification(self, task, queue_id: int | None = None) -> bool:
        if not task or not task.buyer_team or task.buyer_team.allow_archives:
            logger.info(f"Notification skipped for task {task.id}: archives allowed or no buyer team")
            if queue_id:
                await self.db_repo.notifications.update_queue_status(queue_id, NotificationStatus.SUCCESS)
            return True
        user = await self.db_repo.user.get_user(task.created_by_id)
        data = {
            "task_id": task.id,
            "task_type": task.task_type.value,
            "status": task.task_status.value,
            "buyer": user.username,
            "media_files": task.files,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(config.notifications.url),
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.notifications.api_key}",
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed with status {response.status_code}: {response.text}")

        logger.info(f"Notification sent successfully for task {task.id}")
        if queue_id:
            await self.db_repo.notifications.update_queue_status(queue_id, NotificationStatus.SUCCESS)
        else:
            await self.db_repo.notifications.add_queue(task_id=task.id, status=NotificationStatus.SUCCESS)
        return True

    async def _retry_failed_notifications(self):
        failed_tasks = await self.db_repo.notifications.get_failed_queue()
        for failed_task in failed_tasks:
            try:
                if await self._send_notification(failed_task.task_id, failed_task.id):
                    logger.info(f"Retry successful for task {failed_task.task_id}")
            except Exception as e:
                logger.warning(f"Retry failed for task {failed_task.task_id}: {e}")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def send_notification(self, task):
        try:
            if await self._send_notification(task):
                await self._retry_failed_notifications()
        except Exception as e:
            logger.error(f"Failed to send notification for task {task.id} after retries: {e}")
            print(f"Failed to send notification for task {task.id} after retries: {e}")
            await self.db_repo.notifications.add_queue(task_id=task.id, status=NotificationStatus.FAILURE)
