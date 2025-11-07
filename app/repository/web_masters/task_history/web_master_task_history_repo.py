import structlog
from fastapi import HTTPException
from sqlalchemy import insert, select
from sqlalchemy.orm import aliased

from app.models import User, WebMasterTask, WebMasterTaskHistory
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.web_masters.task_history.base import WebMasterTaskBaseRepository
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.enums.user import UserRole

logger = structlog.get_logger()


class WebMasterTaskHistoryRepository(WebMasterTaskBaseRepository, DatabaseEngineRepository):
    async def last_task_history(self, task_id: int):
        async with self.session_maker() as db:
            last_task_history = await db.execute(
                select(WebMasterTaskHistory)
                .where(WebMasterTaskHistory.task_id == task_id)
                .order_by(WebMasterTaskHistory.id.desc())
                .limit(1)
            )

            last_task_history = last_task_history.scalar_one_or_none()

            if last_task_history:
                logger.info(f"Last Task History: {last_task_history.__dict__}")
            else:
                logger.info("No previous task history found.")

            return last_task_history

    async def assign_task_history(self, user: User, task_id: int, lead_id: int, assigned_web_master_id: int):
        async with self.session_maker() as db:
            if user.role != UserRole.lead_web_master:
                raise HTTPException(status_code=403, detail="Only Lead Web Master can assign tasks")

            get_last_task_history = await self.last_task_history(task_id)

            buyer_id = get_last_task_history.buyer_id if get_last_task_history else None

            stmt = insert(WebMasterTaskHistory).values(
                task_id=task_id,
                lead_id=lead_id,
                assigned_web_master_id=assigned_web_master_id,
                event="assign",
                event_info=str(assigned_web_master_id),
                buyer_id=buyer_id,
            )

            await db.execute(stmt)
            await db.commit()

    async def change_status_history(self, task_id: int, task_status: WebMasterTaskStatus, changed_by: User):
        async with self.session_maker() as db:
            get_last_task_history = await self.last_task_history(task_id)

            lead_id = get_last_task_history.lead_id if get_last_task_history else None
            buyer_id = get_last_task_history.buyer_id if get_last_task_history else None
            assigned_web_master_id = get_last_task_history.assigned_web_master_id if get_last_task_history else None

            if not assigned_web_master_id:
                task_data = await db.execute(select(WebMasterTask.assigned_to_id).where(WebMasterTask.id == task_id))

                assigned_web_master_id = task_data.scalar_one_or_none()

            stmt = insert(WebMasterTaskHistory).values(
                task_id=task_id,
                buyer_id=buyer_id,
                lead_id=lead_id,
                assigned_web_master_id=assigned_web_master_id,
                event="status",
                event_info=task_status.value,
                changed_by_id=changed_by.id,
            )

            await db.execute(stmt)
            await db.commit()

    async def get_task_history(
        self,
        task_id: int,
    ):
        async with self.session_maker() as db:
            buyer_user = aliased(User, name="buyer_user")
            lead_user = aliased(User, name="lead_user")
            web_master_user = aliased(User, name="web_master_user")

            stmt = (
                select(
                    WebMasterTaskHistory.id,
                    WebMasterTaskHistory.task_id,
                    WebMasterTaskHistory.event,
                    WebMasterTaskHistory.event_info,
                    buyer_user.username.label("buyer_username"),
                    lead_user.username.label("lead_username"),
                    web_master_user.username.label("assigned_web_master_username"),
                )
                .join(buyer_user, WebMasterTaskHistory.buyer_id == buyer_user.id, isouter=True)
                .join(lead_user, WebMasterTaskHistory.lead_id == lead_user.id, isouter=True)
                .join(web_master_user, WebMasterTaskHistory.assigned_web_master_id == web_master_user.id, isouter=True)
                .where(WebMasterTaskHistory.task_id == task_id)
            )

            result = await db.execute(stmt)

            if task_history := result.mappings().all():
                return task_history

            raise HTTPException(status_code=404, detail="Task history not found")

    async def record_event(
        self,
        *,
        task_id: int,
        event: str,
        event_info: str,
        changed_by: User | None = None,
        lead_id: int | None = None,
        assigned_web_master_id: int | None = None,
        buyer_id: int | None = None,
    ) -> None:
        async with self.session_maker() as db:
            last = await self.last_task_history(task_id)

            stmt = insert(WebMasterTaskHistory).values(
                task_id=task_id,
                buyer_id=buyer_id if buyer_id is not None else (last.buyer_id if last else None),
                lead_id=lead_id if lead_id is not None else (last.lead_id if last else None),
                assigned_web_master_id=(
                    assigned_web_master_id
                    if assigned_web_master_id is not None
                    else (last.assigned_web_master_id if last else None)
                ),
                event=event,
                event_info=event_info,
                changed_by_id=changed_by.id if changed_by else None,
            )
            await db.execute(stmt)
            await db.commit()
