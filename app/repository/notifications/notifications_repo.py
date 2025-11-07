from sqlalchemy import delete, select, update

from app.models import NotificationQueue, NotificationStatus
from app.repository.engine.database import DatabaseEngineRepository


class NotificationsRepository(DatabaseEngineRepository):
    async def add_queue(self, task_id: int, status: NotificationStatus):
        async with self.session_maker() as db:
            queue_entry = NotificationQueue(task_id=task_id, status=status)
            db.add(queue_entry)
            await db.commit()

    async def get_failed_queue(self):
        async with self.session_maker() as db:
            result = await db.execute(
                select(NotificationQueue).where(NotificationQueue.status == NotificationStatus.FAILURE)
            )
            return result.scalars().all()

    async def update_queue_status(self, queue_id: int, status: NotificationStatus):
        async with self.session_maker() as db:
            stmt = update(NotificationQueue).where(NotificationQueue.id == queue_id).values(status=status)
            await db.execute(stmt)
            await db.commit()

    async def delete_queue(self, queue_id: int):
        async with self.session_maker() as db:
            stmt = delete(NotificationQueue).where(NotificationQueue.id == queue_id)
            await db.execute(stmt)
            await db.commit()
