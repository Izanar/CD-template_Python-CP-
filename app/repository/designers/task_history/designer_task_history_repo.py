from typing import List

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, insert, select
from sqlalchemy.orm import aliased

from app.models import DesignerTaskHistory, User
from app.repository.designers.task_history.base import DesignerTaskHistoryBaseRepository
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole
from app.schemas.task_history import ChangedByUserSchema, DesignerTaskHistoryResponseSchema

logger = structlog.get_logger()


class DesignerTaskHistoryRepository(DesignerTaskHistoryBaseRepository, DatabaseEngineRepository):
    async def last_task_history(self, task_id: int):
        async with self.session_maker() as db:
            last_task_history = await db.execute(
                select(DesignerTaskHistory)
                .where(DesignerTaskHistory.task_id == task_id)
                .order_by(DesignerTaskHistory.id.desc())
                .limit(1)
            )

            last_task_history = last_task_history.scalar_one_or_none()

            if last_task_history:
                logger.info(f"Last Task History: {last_task_history.__dict__}")
            else:
                logger.info("No previous task history found.")

            return last_task_history

    async def assign_task_history(self, user: User, task_id: int, assigned_designer_id: int):
        async with self.session_maker() as db:
            if user.role != UserRole.lead_designer:
                raise HTTPException(status_code=403, detail="Only Lead Designer can assign tasks")

            stmt = insert(DesignerTaskHistory).values(
                task_id=task_id,
                event="assign",
                event_info=f"Assigned to designer ID {assigned_designer_id}",
                changed_by_id=user.id,
            )

            await db.execute(stmt)
            await db.commit()

    async def change_status_history(
        self,
        task_id: int,
        task_status: DesignerTaskStatus,
        changed_by: User,
    ):
        async with self.session_maker() as db:
            stmt = insert(DesignerTaskHistory).values(
                task_id=task_id,
                event="status",
                event_info=task_status.value,
                changed_by_id=changed_by.id,
            )
            await db.execute(stmt)
            await db.commit()

    async def record_event(
        self,
        *,
        task_id: int,
        event: TaskEvent,
        event_info: str,
        description: str | None = None,
        changed_by: User | None = None,
    ) -> None:
        async with self.session_maker() as db:
            try:
                stmt = insert(DesignerTaskHistory).values(
                    task_id=task_id,
                    event=event,
                    event_info=event_info,
                    description=description,
                    changed_by_id=changed_by.id if changed_by else None,
                )
                await db.execute(stmt)
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to record event for task {task_id}: {e}")
                raise

    async def get_task_history(self, task_id: int) -> List[DesignerTaskHistoryResponseSchema]:
        async with self.session_maker() as db:
            changed_by_user = aliased(User, name="changed_by_user")

            stmt = (
                select(
                    DesignerTaskHistory.id,
                    DesignerTaskHistory.task_id,
                    DesignerTaskHistory.event,
                    DesignerTaskHistory.event_info,
                    DesignerTaskHistory.description,
                    DesignerTaskHistory.changed_at,
                    changed_by_user.id.label("user_id"),
                    changed_by_user.username,
                    changed_by_user.role,
                )
                .outerjoin(changed_by_user, DesignerTaskHistory.changed_by_id == changed_by_user.id)
                .where(and_(DesignerTaskHistory.task_id == task_id, DesignerTaskHistory.active == True))
                .order_by(DesignerTaskHistory.changed_at)
            )

            result = await db.execute(stmt)
            rows = result.mappings().all()

            if not rows:
                raise HTTPException(status_code=404, detail="Task history not found")

            status_rows = [row for row in rows if row["event"] == "status"]
            time_deltas = {}
            for i, row in enumerate(status_rows):
                if i > 0:
                    delta = (row["changed_at"] - status_rows[i - 1]["changed_at"]).total_seconds()
                    time_deltas[row["id"]] = delta
                else:
                    time_deltas[row["id"]] = None

            return [
                DesignerTaskHistoryResponseSchema(
                    id=row["id"],
                    task_id=row["task_id"],
                    event=row["event"],
                    event_info=row["event_info"],
                    description=row["description"],
                    changed_at=row["changed_at"],
                    changed_by=(
                        ChangedByUserSchema(
                            id=row["user_id"],
                            username=row["username"],
                            role=row["role"],
                        )
                        if row["user_id"]
                        else None
                    ),
                    time_since_previous=time_deltas.get(row["id"]) if row["event"] == "status" else None,
                )
                for row in rows
            ]
