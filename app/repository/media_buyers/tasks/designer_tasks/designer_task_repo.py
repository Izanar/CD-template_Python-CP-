from datetime import date, datetime, timezone
from typing import Literal

import structlog
from fastapi import HTTPException
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Creative,
    Designer,
    DesignerTask,
    DesignerTaskCelebrity,
    DesignerTaskEdit,
    MediaBuyer,
    TaskNote,
    User,
)
from app.repository.admin.teams.media_buyer_team.utils import check_team_by_id
from app.repository.designers.designer.utils import get_task
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.tasks.designer_tasks.base import (
    DesignerTaskBaseRepository,
)
from app.repository.media_buyers.tasks.designer_tasks.utils import (
    build_designer_task_filters,
    calc_time_spent_seconds,
    check_filter_permissions,
    check_task_permissions,
    ensure_no_unsolved_edit_request,
    get_celebrity_by_id,
    get_geo_by_id,
    get_language_by_id,
    get_next_designer_task_seq,
    get_task_by_id,
    get_task_note,
    get_team_by_id,
    restrict_media_files,
    validate_buyer_edit_permission,
    validate_date_range,
    validate_edit_exists_and_unsolved,
)
from app.repository.media_buyers.tasks.utils import check_task_status, ensure_can_edit_priority, ensure_task_was_updated
from app.repository.utils import build_order_by
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_status import (
    DesignerTaskStatus,
)
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole
from app.schemas.media_buyer import MediaBuyerTaskCreateSchema, MediaBuyerTaskUpdateSchema

logger = structlog.get_logger(__name__)


class DesignerTaskRepository(DesignerTaskBaseRepository, DatabaseEngineRepository):
    async def create_task(
        self, task: MediaBuyerTaskCreateSchema, user: User, task_status: DesignerTaskStatus | None = None
    ):
        async with self.session_maker() as db:
            team_id = await get_team_by_id(db=db, user=user)
            team = await check_team_by_id(team_id=team_id, db=db)

            stmt = insert(DesignerTask).values(
                description=task.description,
                created_by_id=user.id,
                task_type=task.task_type,
                buyer_team_id=team_id,
            )
            if task_status:
                stmt = stmt.values(task_status=task_status)

            if task.geo_id:
                await get_geo_by_id(db, task.geo_id)
                stmt = stmt.values(geo_id=task.geo_id)

            if task.language_id:
                await get_language_by_id(db, task.language_id)
                stmt = stmt.values(language_id=task.language_id)

            unique_celebrity_ids = []
            if task.celebrities:
                unique_celebrity_ids = list(set(task.celebrities))
                for celebrity_id in unique_celebrity_ids:
                    await get_celebrity_by_id(db, celebrity_id)

            stmt = stmt.returning(DesignerTask.id)

            result = await db.execute(stmt)

            task_id = result.scalar_one_or_none()

            if not task_id:
                raise HTTPException(status_code=400, detail="Task creation failed")

            task = await get_task(db=db, task_id=task_id, user=user)

            seq = await get_next_designer_task_seq(
                db=db,
                team_id=team_id,
                team_prefix=team.prefix,
                start_id=team.custom_task_start_id,
            )
            task.title = f"{task.task_prefix}.{seq}"

            if unique_celebrity_ids:
                celebrity_values = [
                    {"task_id": task_id, "celebrity_id": celebrity_id} for celebrity_id in unique_celebrity_ids
                ]
                statement = insert(DesignerTaskCelebrity).values(celebrity_values)
                await db.execute(statement)

            await db.commit()

            return task

    async def create_draft_task(
        self, task: MediaBuyerTaskCreateSchema, user: User, task_status: DesignerTaskStatus | None = None
    ):
        async with self.session_maker() as db:
            await get_team_by_id(db=db, user=user)

            stmt = insert(DesignerTask).values(
                description=task.description,
                created_by_id=user.id,
                task_type=task.task_type,
                task_status=task_status,
            )

            if task.geo_id:
                await get_geo_by_id(db, task.geo_id)
                stmt = stmt.values(geo_id=task.geo_id)

            if task.language_id:
                await get_language_by_id(db, task.language_id)
                stmt = stmt.values(language_id=task.language_id)

            stmt = stmt.returning(DesignerTask.id)
            result = await db.execute(stmt)
            task_id = result.scalar_one_or_none()

            if not task_id:
                raise HTTPException(status_code=400, detail="Task creation failed")

            task = await get_task(db=db, task_id=task_id, user=user)

            draft_count_query = (
                select(func.count())
                .select_from(DesignerTask)
                .where(DesignerTask.created_by_id == user.id, DesignerTask.task_status == DesignerTaskStatus.DRAFT)
            )
            draft_count = await db.scalar(draft_count_query) or 0
            task.title = f"DRAFT{draft_count}"

            await db.commit()

            return task

    async def send_task(self, task_id: int, user: User):
        await self.get_task(task_id=task_id, user=user)
        async with self.session_maker() as db:
            team_id = await get_team_by_id(db=db, user=user)
            team = await check_team_by_id(team_id=team_id, db=db)

            task = await get_task(db=db, task_id=task_id, user=user)

            await check_task_status(
                task=task,
                required_status=DesignerTaskStatus.DRAFT,
                detail=f"Task with ID {task.id} must be in DRAFT status to be sent.",
            )
            seq = await get_next_designer_task_seq(
                db=db,
                team_id=team_id,
                team_prefix=team.prefix,
                start_id=team.custom_task_start_id,
            )
            title = f"{task.task_prefix}.{seq}"

            stmt = (
                update(DesignerTask)
                .where(DesignerTask.id == task_id, DesignerTask.created_by_id == user.id)
                .values(task_status=DesignerTaskStatus.WAITING_TO_ASSIGN, title=title, buyer_team_id=team_id)
                .returning(DesignerTask.id)
            )
            result = await db.execute(stmt)
            updated_task_id = result.scalar_one_or_none()

            await ensure_task_was_updated(updated_task_id=updated_task_id, detail="Failed to send task.")

            await db.commit()

            return await get_task(db=db, task_id=updated_task_id, user=user)

    async def save_and_send_task(self, task: MediaBuyerTaskCreateSchema, task_id: int, user: User):
        await self.get_task(task_id=task_id, user=user)
        async with self.session_maker() as db:
            existing_task = await get_task(db=db, task_id=task_id, user=user)

            await check_task_status(
                task=existing_task,
                required_status=DesignerTaskStatus.DRAFT,
                detail=f"Task with ID {existing_task.id} must be in DRAFT status to be saved and sent.",
            )
            team_id = await get_team_by_id(db=db, user=user)
            team = await check_team_by_id(team_id=team_id, db=db)

            seq = await get_next_designer_task_seq(
                db=db,
                team_id=team_id,
                team_prefix=team.prefix,
                start_id=team.custom_task_start_id,
            )
            title = f"{existing_task.task_prefix}.{seq}"

            update_data = task.model_dump(exclude_unset=True)
            update_data["task_status"] = DesignerTaskStatus.WAITING_TO_ASSIGN
            update_data["title"] = title
            update_data["buyer_team_id"] = team_id

            stmt = (
                update(DesignerTask)
                .where(DesignerTask.id == task_id, DesignerTask.created_by_id == user.id)
                .values(**update_data)
                .returning(DesignerTask.id)
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
        task_type: DesignerTaskTypeEnum | None,
        task_statuses: list[DesignerTaskStatus] | None,
        order_by: str | None = None,
        order_direction: Literal["asc", "desc"] | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
        is_need_to_assign: bool | None = None,
        is_media_buyers_teams: bool | None = None,
        is_high_priority: bool | None = None,
        created_by_id: list[int] | None = None,
        designer_team_ids: list[int] | None = None,
        buyer_team_ids: list[int] | None = None,
        assigned_to_id: list[int] | None = None,
        title: str | None = None,
        is_operational: bool | None = None,
        is_deleted: bool | None = None,
        difficulty_ids: list[int] | None = None,
        vertical: VerticalType | None = None,
        geo_codes: list[int] | None = None,
        ad_name: str | None = None,
    ):
        await check_filter_permissions(
            user=user,
            is_media_buyers_teams=is_media_buyers_teams,
            is_need_to_assign=is_need_to_assign,
            task_statuses=task_statuses,
            created_by_id=created_by_id,
            buyer_team_ids=buyer_team_ids,
            assigned_to_id=assigned_to_id,
            is_operational=is_operational,
            is_deleted=is_deleted,
            difficulty_ids=difficulty_ids,
        )
        await validate_date_range(created_from=created_from, created_to=created_to)

        async with self.session_maker() as db:
            filters = await build_designer_task_filters(
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
                buyer_team_ids=buyer_team_ids,
                assigned_to_id=assigned_to_id,
                title=title,
                is_operational=is_operational,
                is_deleted=is_deleted,
                difficulty_ids=difficulty_ids,
                designer_team_ids=designer_team_ids,
                vertical=vertical,
                geo_codes=geo_codes,
                ad_name=ad_name,
            )

            count_stmt = select(func.count()).select_from(DesignerTask).where(*filters)
            total_result = await db.execute(count_stmt)
            total_count = total_result.scalar_one()

            stmt = (
                select(DesignerTask)
                .where(*filters)
                .options(
                    joinedload(DesignerTask.difficulties),
                    joinedload(DesignerTask.media_files),
                    joinedload(DesignerTask.edits),
                    selectinload(DesignerTask.evaluations),
                    selectinload(DesignerTask.assigned_to).selectinload(Designer.user),
                    selectinload(DesignerTask.assigned_to).selectinload(Designer.teams),
                    selectinload(DesignerTask.created_by).selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
                    selectinload(DesignerTask.notes),
                    selectinload(DesignerTask.creatives).selectinload(Creative.media_files),
                    selectinload(DesignerTask.celebrity_relations).selectinload(DesignerTaskCelebrity.celebrity),
                    joinedload(DesignerTask.buyer_team),
                    joinedload(DesignerTask.geo_ref),
                )
                .limit(limit)
                .offset(offset)
            )

            stmt = build_order_by(stmt, DesignerTask, order_by, order_direction)
            result = await db.execute(stmt)
            tasks = result.unique().scalars().all()

            hide_created_by = user.role in (UserRole.designer,)
            is_restricted_role = user.role not in (UserRole.lead_designer, UserRole.admin)

            for task in tasks:
                task.time_spent_seconds = await calc_time_spent_seconds(db, task.id)

                task.note = await get_task_note(db, task.id, user)
                if is_restricted_role:
                    if hide_created_by:
                        task.created_by = None
                    restrict_media_files(task=task, user=user)
            return tasks, total_count

    async def get_task(self, task_id: int | None, user: User) -> DesignerTask:
        async with self.session_maker() as db:
            stmt = (
                select(DesignerTask)
                .where(DesignerTask.id == task_id)
                .options(
                    selectinload(DesignerTask.media_files),
                    selectinload(DesignerTask.difficulties),
                    selectinload(DesignerTask.edits),
                    selectinload(DesignerTask.evaluations),
                    selectinload(DesignerTask.assigned_to).selectinload(Designer.user),
                    selectinload(DesignerTask.assigned_to).selectinload(Designer.teams),
                    selectinload(DesignerTask.created_by).selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
                    selectinload(DesignerTask.notes),
                    selectinload(DesignerTask.creatives).selectinload(Creative.media_files),
                    selectinload(DesignerTask.celebrity_relations).selectinload(DesignerTaskCelebrity.celebrity),
                    joinedload(DesignerTask.buyer_team),
                )
            )

            if user.role != UserRole.admin:
                stmt = stmt.where(DesignerTask.is_deleted.is_(False))

            task = await db.scalar(stmt)

            if not task:
                raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

            await check_task_permissions(task=task, user=user)

            restrict_media_files(task=task, user=user)
            task.note = await get_task_note(db, task.id, user)
            task.time_spent_seconds = await calc_time_spent_seconds(db, task.id)

            if user.role in (UserRole.designer,):
                task.created_by = None

            return task

    async def update_task(self, task: MediaBuyerTaskUpdateSchema, task_id: int, user: User):
        async with self.session_maker() as db:
            existing_task = await get_task_by_id(db=db, task_id=task_id)

            await check_task_permissions(task=existing_task, user=user)

            await check_task_status(
                task=existing_task,
                forbidden_status=DesignerTaskStatus.COMPLETED,
                detail=f"Task with ID {existing_task.id} cannot be updated because it is already COMPLETED.",
            )
            update_data = task.model_dump(exclude_unset=True)

            await ensure_can_edit_priority(user=user, task=existing_task, update_data=update_data, db=db)

            if any(key != "is_high_priority" for key in update_data):
                await check_task_status(
                    task=existing_task,
                    required_status=DesignerTaskStatus.DRAFT,
                    detail=f"Task with ID {existing_task.id} must be in DRAFT status to update its details.",
                )

            if "geo_id" in update_data:
                geo_id = update_data["geo_id"]
                if geo_id is not None and geo_id != existing_task.geo_id:
                    await get_geo_by_id(db, geo_id)

            if "language_id" in update_data:
                language_id = update_data["language_id"]
                if language_id is not None and language_id != existing_task.language_id:
                    await get_language_by_id(db, language_id)

            celebrities_to_update = update_data.pop("celebrities", None)

            if update_data:
                stmt = update(DesignerTask).where(DesignerTask.id == task_id).values(**update_data)
                await db.execute(stmt)

            if celebrities_to_update is not None:
                unique_celebrity_ids = list(set(celebrities_to_update))
                for celebrity_id in unique_celebrity_ids:
                    await get_celebrity_by_id(db, celebrity_id)

                await db.execute(select(DesignerTaskCelebrity).where(DesignerTaskCelebrity.task_id == task_id))
                existing_celebrity_ids = {
                    dtc.celebrity_id
                    for dtc in await db.scalars(
                        select(DesignerTaskCelebrity).where(DesignerTaskCelebrity.task_id == task_id)
                    )
                }

                celebrities_to_add = set(unique_celebrity_ids) - existing_celebrity_ids
                celebrities_to_remove = existing_celebrity_ids - set(unique_celebrity_ids)

                if celebrities_to_remove:
                    await db.execute(
                        delete(DesignerTaskCelebrity).where(
                            DesignerTaskCelebrity.task_id == task_id,
                            DesignerTaskCelebrity.celebrity_id.in_(celebrities_to_remove),
                        )
                    )

                if celebrities_to_add:
                    celebrity_values = [
                        {"task_id": task_id, "celebrity_id": celebrity_id} for celebrity_id in celebrities_to_add
                    ]
                    statement = insert(DesignerTaskCelebrity).values(celebrity_values)
                    await db.execute(statement)

            await db.commit()

            return await self.get_task(task_id=task_id, user=user)

    async def delete_task(self, task_id: int, user: User):
        async with self.session_maker() as db:
            task = await self.get_task(task_id=task_id, user=user)

            if user.role == UserRole.admin:
                pass
            elif user.role == UserRole.lead_designer:
                await check_task_status(
                    task,
                    allowed_statuses=[
                        DesignerTaskStatus.WAITING_TO_ASSIGN,
                        DesignerTaskStatus.WAITING_TO_START,
                        DesignerTaskStatus.IN_PROGRESS,
                        DesignerTaskStatus.REQUESTED_CHANGES,
                        DesignerTaskStatus.UNDER_TL_REVIEW,
                    ],
                    detail=(f"Lead designer can't delete task in {task.task_status.value} status."),
                )
            else:
                await check_task_status(
                    task,
                    required_status=DesignerTaskStatus.DRAFT,
                    detail=f"Task with ID {task.id} must be in DRAFT status to be deleted.",
                )
            updated_task = (
                await db.execute(
                    update(DesignerTask)
                    .where(DesignerTask.id == task_id)
                    .values(is_deleted=True)
                    .returning(DesignerTask)
                )
            ).scalar_one()

            await db.commit()
            return updated_task

    async def request_edit_task(self, current_user: User, task_id: int, description: str) -> DesignerTask:
        async with self.session_maker() as db:
            await get_task_by_id(db=db, task_id=task_id)

            task = await db.scalar(
                select(DesignerTask).options(selectinload(DesignerTask.edits)).where(DesignerTask.id == task_id)
            )

            await validate_buyer_edit_permission(task=task, current_user=current_user)
            await ensure_no_unsolved_edit_request(db=db, task_id=task.id)

            task.task_status = DesignerTaskStatus.REQUESTED_CHANGES
            task_edit = DesignerTaskEdit(task_id=task.id, description=description)
            db.add(task_edit)

            await db.commit()
            await db.refresh(task_edit)

            return await self.get_task(task_id=task_id, user=current_user)

    async def approve_edit_task(self, current_user: User, edit_id: int, task_id: int) -> DesignerTask:
        async with self.session_maker() as db:
            await get_task_by_id(db=db, task_id=task_id)

            edit = await db.scalar(
                select(DesignerTaskEdit)
                .options(selectinload(DesignerTaskEdit.task))
                .where(DesignerTaskEdit.id == edit_id)
            )

            await validate_edit_exists_and_unsolved(edit=edit)

            task = edit.task

            await check_task_permissions(task=task, user=current_user)

            edit.solved_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(edit)

            return await self.get_task(task_id=task_id, user=current_user)

    async def add_task_note(self, task_id: int, author: User, content: str) -> DesignerTask:
        async with self.session_maker() as db:
            async with db.begin():
                task = await self.get_task(task_id, user=author)

                is_team = author.role == UserRole.lead_designer
                author_clause = TaskNote.author_id == author.id if not is_team else TaskNote.author_id.is_(None)

                stmt = (
                    select(TaskNote)
                    .where(
                        TaskNote.designer_task_id == task.id,
                        TaskNote.is_team_note == is_team,
                        author_clause,
                    )
                    .with_for_update()
                    .limit(1)
                )
                note = await db.scalar(stmt)

                if note:
                    note.content = content
                    note.updated_at = func.now()
                else:
                    db.add(
                        TaskNote(
                            designer_task_id=task.id,
                            author_id=None if is_team else author.id,
                            is_team_note=is_team,
                            content=content,
                        )
                    )
        return await self.get_task(task_id, user=author)
