from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import update

from app.models import User, WebMasterTask
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.web_masters.web_master.base import WebMasterBaseRepository
from app.repository.web_masters.web_master.utils import (
    build_task_filters,
    get_task,
)
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.enums.user import UserRole


class WebMasterRepository(WebMasterBaseRepository, DatabaseEngineRepository):
    async def update_task_status(self, task_id: int, task_status: WebMasterTaskStatus, current_user: User):
        async with self.session_maker() as db:
            existing_task = await get_task(db=db, task_id=task_id, user=current_user)

            filters = await build_task_filters(user=current_user, task_id=task_id)

            update_values = {"task_status": task_status}

            if task_status == WebMasterTaskStatus.COMPLETED:
                update_values["completed_at"] = datetime.now(timezone.utc)

            if (
                task_status == WebMasterTaskStatus.UNDER_TL_REVIEW
                and current_user.role == UserRole.lead_web_master
                and existing_task.assigned_to_id == current_user.id
            ):
                if not existing_task.media_files:
                    raise HTTPException(
                        status_code=409, detail="You must attach one media file before send task on review"
                    )
                update_values["task_status"] = WebMasterTaskStatus.UNDER_BUYER_REVIEW

            stmt = update(WebMasterTask).where(*filters).values(**update_values).returning(WebMasterTask.id)

            result = await db.execute(stmt)
            updated_task_id = result.scalar_one_or_none()

            if not updated_task_id:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            await db.commit()

            return await get_task(db=db, task_id=task_id, user=current_user)
