from datetime import date, datetime, timezone
from typing import Literal

import structlog
from fastapi import HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import joinedload, selectinload

from app.models import MediaBuyer, User, WebMaster, WebMasterTask, WebMasterTaskEdit
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.tasks.utils import check_task_status, ensure_task_was_updated
from app.repository.media_buyers.tasks.web_master_tasks.base import WebMasterTaskBaseRepository
from app.repository.media_buyers.tasks.web_master_tasks.utils import (
    add_default_difficulty_if_needed,
    build_web_master_task_filters,
    check_filter_permissions,
    check_task_permissions,
    check_task_type_exists,
    create_task_history,
    ensure_lead,
    ensure_no_unsolved_edit_request,
    get_next_web_master_task_seq,
    get_task_by_id,
    get_team_by_id,
    validate_buyer_edit_permission,
    validate_date_range,
    validate_edit_exists_and_unsolved,
    validate_webmaster_task_primitives,
)
from app.repository.utils import build_order_by_web_master_tasks
from app.repository.web_masters.web_master.utils import get_task
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.enums.user import UserRole
from app.schemas.media_buyer import MediaBuyerTaskCreateSchema, WebMasterTaskCreateSchema

logger = structlog.get_logger(__name__)


class WebMasterTaskRepository(WebMasterTaskBaseRepository, DatabaseEngineRepository):
    async def create_task(
        self, task: WebMasterTaskCreateSchema, user: User, task_status: WebMasterTaskStatus | None = None
    ):
        async with self.session_maker() as db:
            task_type = await check_task_type_exists(db, task.task_type_id)

            validate_webmaster_task_primitives(task)

            team_id = await get_team_by_id(db=db, user=user)
            seq = await get_next_web_master_task_seq(db=db, team_id=team_id)

            stmt = insert(WebMasterTask).values(
                description=task.description,
                created_by_id=user.id,
                task_type_id=task.task_type_id,
                project_type=task.project_type,
                funnel_id=task.funnel_id,
                site_name_id=task.site_name_id,
                celebrity_id=task.celebrity_id,
            )

            if task_status:
                stmt = stmt.values(task_status=task_status)

            stmt = stmt.returning(WebMasterTask.id)

            result = await db.execute(stmt)

            task_id = result.scalar_one_or_none()

            if not task_id:
                raise HTTPException(status_code=400, detail="Task creation failed")

            await add_default_difficulty_if_needed(db, task_id, task_type.name)

            task = await get_task(db=db, task_id=task_id, user=user)

            task.title = f"{team_id}.{seq}"

            await db.commit()

            await create_task_history(db=db, task_id=task_id, buyer_id=user.id)

            return task

    async def send_task(self, task_id: int, user: User):
        task = await self.get_task(task_id=task_id, user=user)

        await check_task_status(
            task=task,
            required_status=WebMasterTaskStatus.DRAFT,
            detail=f"Task with ID {task.id} must be in DRAFT status to be sent.",
        )

        async with self.session_maker() as db:
            stmt = (
                update(WebMasterTask)
                .where(WebMasterTask.id == task_id, WebMasterTask.created_by_id == user.id)
                .values(task_status=WebMasterTaskStatus.WAITING_TO_ASSIGN)
                .returning(WebMasterTask.id)
            )
            result = await db.execute(stmt)
            updated_task_id = result.scalar_one_or_none()

            await ensure_task_was_updated(updated_task_id=updated_task_id, detail="Failed to send task.")

            await db.commit()

            return await get_task(db=db, task_id=updated_task_id, user=user)

    async def save_and_send_task(self, task: MediaBuyerTaskCreateSchema, task_id: int, user: User):
        existing_task = await self.get_task(task_id=task_id, user=user)

        await check_task_status(
            task=existing_task,
            required_status=WebMasterTaskStatus.DRAFT,
            detail=f"Task with ID {existing_task.id} must be in DRAFT status to be saved and sent.",
        )

        update_data = task.model_dump(exclude_unset=True)
        update_data["task_status"] = WebMasterTaskStatus.WAITING_TO_ASSIGN

        async with self.session_maker() as db:
            stmt = (
                update(WebMasterTask)
                .where(WebMasterTask.id == task_id, WebMasterTask.created_by_id == user.id)
                .values(**update_data)
                .returning(WebMasterTask.id)
            )

            result = await db.execute(stmt)
            updated_task_id = result.scalar_one_or_none()

            await ensure_task_was_updated(updated_task_id=updated_task_id, detail="Failed to save and send task.")

            await db.commit()

            return await get_task(db=db, task_id=updated_task_id, user=user)

    async def get_user_tasks(
        self,
        user: User,
        limit: int,
        offset: int,
        task_type: int | None,
        task_statuses: WebMasterTaskStatus | None,
        order_by: str | None = None,
        order_direction: Literal["asc", "desc"] | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
        is_need_to_assign: bool | None = None,
        is_media_buyers_teams: bool | None = None,
        is_high_priority: bool | None = None,
        created_by_id: int | None = None,
        buyer_team_id: int | None = None,
        assigned_to_id: int | None = None,
        title: str | None = None,
        vertical: VerticalType | None = None,
        funnel_ids: list[int] | None = None,
        celebrity_ids: list[int] | None = None,
        site_name_ids: list[int] | None = None,
        is_deleted: bool | None = None,
        geo_codes: list[int] | None = None,
    ):
        await check_filter_permissions(
            user=user,
            is_media_buyers_teams=is_media_buyers_teams,
            is_need_to_assign=is_need_to_assign,
            task_statuses=task_statuses,
            created_by_id=created_by_id,
            buyer_team_id=buyer_team_id,
            assigned_to_id=assigned_to_id,
        )

        await validate_date_range(created_from=created_from, created_to=created_to)

        async with self.session_maker() as db:
            filters = await build_web_master_task_filters(
                db=db,
                user=user,
                task_type=task_type,
                task_statuses=task_statuses,
                created_from=created_from,
                created_to=created_to,
                is_need_to_assign=is_need_to_assign,
                is_media_buyers_teams=is_media_buyers_teams,
                is_high_priority=is_high_priority,
                created_by_id=created_by_id,
                buyer_team_id=buyer_team_id,
                assigned_to_id=assigned_to_id,
                title=title,
                vertical=vertical,
                funnel_ids=funnel_ids,
                celebrity_ids=celebrity_ids,
                site_name_ids=site_name_ids,
                is_deleted=is_deleted,
                geo_codes=geo_codes,
            )

            count_stmt = select(func.count()).select_from(WebMasterTask).where(*filters)
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar_one_or_none()

            stmt = (
                select(WebMasterTask)
                .where(*filters)
                .options(
                    joinedload(WebMasterTask.funnel_ref),
                    joinedload(WebMasterTask.site_name_ref),
                    joinedload(WebMasterTask.celebrity_ref),
                    joinedload(WebMasterTask.geo_ref),
                    joinedload(WebMasterTask.task_type),
                    joinedload(WebMasterTask.difficulties),
                    joinedload(WebMasterTask.buyer_team),
                    joinedload(WebMasterTask.media_files),
                    joinedload(WebMasterTask.edits),
                    selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.user),
                    selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.teams),
                    selectinload(WebMasterTask.created_by).selectinload(MediaBuyer.user),
                )
                .limit(limit)
                .offset(offset)
            )

            stmt = build_order_by_web_master_tasks(stmt, WebMasterTask, order_by, order_direction)
            result = await db.execute(stmt)
            tasks = result.unique().scalars().all()
            hide_created_by = user.role in (UserRole.web_master, UserRole.media_buyer)

            if user.role not in (UserRole.lead_web_master, UserRole.admin):
                for task in tasks:
                    if hide_created_by:
                        task.created_by = None

            return tasks, total_count

    async def get_task(self, task_id: int | None, user: User) -> WebMasterTask:
        async with self.session_maker() as db:
            stmt = (
                select(WebMasterTask)
                .where(WebMasterTask.id == task_id)
                .options(
                    joinedload(WebMasterTask.funnel_ref),
                    joinedload(WebMasterTask.site_name_ref),
                    joinedload(WebMasterTask.celebrity_ref),
                    joinedload(WebMasterTask.geo_ref),
                    joinedload(WebMasterTask.buyer_team),
                    selectinload(WebMasterTask.task_type),
                    selectinload(WebMasterTask.media_files),
                    selectinload(WebMasterTask.difficulties),
                    selectinload(WebMasterTask.edits),
                    selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.user),
                    selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.teams),
                    selectinload(WebMasterTask.created_by).selectinload(MediaBuyer.user),
                )
            )
            if user.role != UserRole.admin:
                stmt = stmt.where(WebMasterTask.is_deleted.is_(False))
            task = await db.scalar(stmt)

            await get_task_by_id(db=db, task_id=task_id)
            await check_task_permissions(task=task, user=user)

            if user.role in (UserRole.web_master, UserRole.media_buyer):
                task.created_by = None

            return task

    async def update_task(self, task: WebMasterTaskCreateSchema, task_id: int, user: User):
        async with self.session_maker() as db:
            existing_task = await get_task_by_id(db=db, task_id=task_id)

            await check_task_type_exists(db, task.task_type_id)

            await check_task_status(
                existing_task,
                forbidden_status=WebMasterTaskStatus.COMPLETED,
                detail=f"Task with ID {existing_task.id} cannot be updated because it is already COMPLETED.",
            )

            update_data = task.model_dump(exclude_unset=True)

            if any(key != "is_high_priority" for key in update_data):
                await check_task_status(
                    task=existing_task,
                    required_status=WebMasterTaskStatus.DRAFT,
                    detail=f"Task with ID {existing_task.id} must be in DRAFT status to update its details.",
                )

            if "task_type_id" in update_data:
                await check_task_type_exists(db, update_data["task_type_id"])
            ensure_lead(update_data, user)
            stmt = update(WebMasterTask).where(WebMasterTask.id == task_id).values(**update_data)

            await db.execute(stmt)
            await db.commit()

            return await self.get_task(task_id=task_id, user=user)

    async def delete_task(self, task_id: int, user: User):
        async with self.session_maker() as db:
            task = await self.get_task(task_id=task_id, user=user)
            if user.role == UserRole.admin:
                pass
            elif user.role == UserRole.lead_web_master:
                await check_task_status(
                    task,
                    required_status=WebMasterTaskStatus.WAITING_TO_ASSIGN,
                    detail=f"Task with ID {task.id} must be in WAITING_TO_ASSIGN status"
                    f" to be deleted by a lead web master.",
                )
            else:
                await check_task_status(
                    task,
                    required_status=WebMasterTaskStatus.DRAFT,
                    detail=f"Task with ID {task.id} must be in DRAFT status to be deleted.",
                )

            stmt = (
                update(WebMasterTask)
                .where(WebMasterTask.id == task_id)
                .values(is_deleted=True)
                .returning(WebMasterTask)
            )

            result = await db.execute(stmt)
            await db.commit()

            return result.scalar()

    async def request_edit_task(self, current_user: User, task_id: int, description: str) -> WebMasterTask:
        async with self.session_maker() as db:
            await get_task_by_id(db=db, task_id=task_id)

            task = await db.scalar(
                select(WebMasterTask).options(selectinload(WebMasterTask.edits)).where(WebMasterTask.id == task_id)
            )

            await validate_buyer_edit_permission(task=task, current_user=current_user)
            await ensure_no_unsolved_edit_request(db=db, task_id=task.id)

            task.task_status = WebMasterTaskStatus.REQUESTED_CHANGES
            task_edit = WebMasterTaskEdit(task_id=task.id, description=description)
            db.add(task_edit)

            await db.commit()
            await db.refresh(task_edit)

            return await self.get_task(task_id=task_id, user=current_user)

    async def approve_edit_task(self, current_user: User, edit_id: int, task_id: int) -> WebMasterTaskEdit:
        async with self.session_maker() as db:
            await get_task_by_id(db=db, task_id=task_id)

            edit = await db.scalar(
                select(WebMasterTaskEdit)
                .options(selectinload(WebMasterTaskEdit.task))
                .where(WebMasterTaskEdit.id == edit_id)
            )

            await validate_edit_exists_and_unsolved(edit=edit)

            task = edit.task

            await check_task_permissions(task=task, user=current_user)

            edit.solved_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(edit)

            return await self.get_task(task_id=task_id, user=current_user)
