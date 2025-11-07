from datetime import date, datetime, time

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, delete, func, insert, select, update

from app.models import (
    DesignersTeam,
    DesignersTeamMembers,
    DesignerTask,
    DesignerTaskCelebrity,
    DesignerTaskDifficulty,
    DifficultyLevel,
    User,
)
from app.repository.designers.designer.utils import get_task
from app.repository.designers.lead_designer.base import LeadDesignerBaseRepository
from app.repository.designers.lead_designer.utils import get_user
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.tasks.designer_tasks.utils import get_celebrity_by_id
from app.repository.media_buyers.tasks.utils import check_task_status
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole
from app.schemas.media_buyers.tasks.designer_tasks import (
    CreateOperationDesignerTaskSchema,
    UpdateDesignerTaskSchema,
)

logger = structlog.get_logger(__name__)


class LeadDesignerRepository(LeadDesignerBaseRepository, DatabaseEngineRepository):
    async def get_completed_tasks(
        self,
        user_id: int | None,
        team_id: int | None,
        start_date: date,
        end_date: date,
        task_status: DesignerTaskStatus,
    ):
        async with self.session_maker() as db:
            filters = [
                DesignerTask.task_status == task_status,
                DesignerTask.completed_at >= datetime.combine(start_date, time.min),
                DesignerTask.completed_at <= datetime.combine(end_date, time.max),
            ]

            if user_id is not None:
                filters.append(DesignerTask.assigned_to_id == user_id)

            if team_id is not None:
                filters.append(
                    DesignerTask.assigned_to_id.in_(
                        select(DesignersTeamMembers.designer_id).where(DesignersTeamMembers.team_id == team_id)
                    )
                )

            stmt = (
                select(
                    DesignerTask.assigned_to_id.label("user_id"),
                    func.count(func.distinct(DesignerTask.id)).label("completed_tasks"),
                    (func.coalesce(func.sum(func.distinct(DifficultyLevel.points)), 0)).label("total_points"),
                )
                .select_from(DesignerTask)
                .outerjoin(DifficultyLevel, DesignerTask.difficulties)
                .where(and_(*filters))
                .group_by(DesignerTask.assigned_to_id)
            )

            result = await db.execute(stmt)
            return result.all()

    async def update_designer_task(self, task_info: UpdateDesignerTaskSchema, user: User):
        async with self.session_maker() as db:
            existing_task = await get_task(db=db, task_id=task_info.task_id, user=user)
            if not existing_task:
                raise HTTPException(status_code=404, detail="Task not found")

            exclude_fields = {"task_id", "difficulty_ids", "assigned_to_id", "celebrities"}
            update_data = task_info.dict(exclude_unset=True, exclude=exclude_fields)

            if "assigned_to_id" in task_info.__fields_set__:
                if task_info.assigned_to_id is not None:
                    if existing_task.task_status in (
                        DesignerTaskStatus.COMPLETED,
                        DesignerTaskStatus.UNDER_BUYER_REVIEW,
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail="Designer can`t be assigned when task status is 'COMPLETED' or 'UNDER_BUYER_REVIEW'",
                        )

                    has_difficulty = bool(task_info.difficulty_ids or existing_task.difficulties)
                    if not has_difficulty:
                        raise HTTPException(status_code=409, detail="Task cannot be assigned without difficulty")

                    await get_user(db=db, user_id=task_info.assigned_to_id)
                    if existing_task.assigned_to_id != task_info.assigned_to_id:
                        update_data["assigned_to_id"] = task_info.assigned_to_id
                        update_data["task_status"] = DesignerTaskStatus.WAITING_TO_START

                elif existing_task.assigned_to_id is not None:
                    update_data["assigned_to_id"] = None
                    update_data["task_status"] = DesignerTaskStatus.WAITING_TO_ASSIGN

            if update_data:
                await db.execute(update(DesignerTask).where(DesignerTask.id == task_info.task_id).values(**update_data))

            if task_info.difficulty_ids is not None:
                await db.execute(
                    delete(DesignerTaskDifficulty).where(DesignerTaskDifficulty.task_id == task_info.task_id)
                )
                difficulty_ids = [item.id for item in task_info.difficulty_ids if item.id is not None]
                if difficulty_ids:
                    await db.execute(
                        insert(DesignerTaskDifficulty),
                        [{"task_id": task_info.task_id, "difficulty_id": diff_id} for diff_id in difficulty_ids],
                    )

            if task_info.celebrities is not None:
                if user.role == UserRole.designer:
                    await check_task_status(
                        task=existing_task,
                        required_status=DesignerTaskStatus.IN_PROGRESS,
                        detail="Designers can only update celebrities when task is IN_PROGRESS",
                    )

                unique_ids = list(set(task_info.celebrities))
                for celeb_id in unique_ids:
                    await get_celebrity_by_id(db, celeb_id)

                existing_ids = {
                    c.celebrity_id
                    for c in await db.scalars(
                        select(DesignerTaskCelebrity).where(DesignerTaskCelebrity.task_id == task_info.task_id)
                    )
                }

                to_add = set(unique_ids) - existing_ids
                to_remove = existing_ids - set(unique_ids)

                if to_remove:
                    await db.execute(
                        delete(DesignerTaskCelebrity).where(
                            DesignerTaskCelebrity.task_id == task_info.task_id,
                            DesignerTaskCelebrity.celebrity_id.in_(to_remove),
                        )
                    )

                if to_add:
                    await db.execute(
                        insert(DesignerTaskCelebrity),
                        [{"task_id": task_info.task_id, "celebrity_id": cid} for cid in to_add],
                    )

            await db.commit()
            db.expire(existing_task, ["difficulties"])
            await db.refresh(existing_task)
            return existing_task

    async def view_designers_load(self, is_my_teams: bool, user_id: int):
        async with self.session_maker() as db:
            # Подсчет задач, назначенных на дизайнеров
            task_count_subquery = (
                select(
                    DesignerTask.assigned_to_id,
                    func.count(DesignerTask.id).label("assigned_tasks_count"),
                )
                .group_by(DesignerTask.assigned_to_id)
                .subquery()
            )

            stmt = (
                select(User, task_count_subquery.c.assigned_tasks_count)
                .where(User.role == UserRole.designer)
                .outerjoin(task_count_subquery, task_count_subquery.c.assigned_to_id == User.id)
            )

            if is_my_teams:
                team_members_stmt = (
                    select(DesignersTeamMembers.designer_id)
                    .join(DesignersTeam, DesignersTeam.id == DesignersTeamMembers.team_id)
                    .where(DesignersTeam.lead_id == user_id)
                )

                team_members_ids = await db.scalars(team_members_stmt)
                team_members_ids = list(team_members_ids)  # Преобразуем в список ID

                stmt = stmt.where(User.id.in_(team_members_ids))

            result = await db.execute(stmt)
            designers = []
            for user, assigned_tasks_count in result.all():
                designers.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "created_at": user.created_at,
                        "role": user.role,
                        "assigned_tasks_count": assigned_tasks_count or 0,
                    }
                )

            return designers

    async def get_designers_by_team(self, team_id: list[int]) -> list[User]:
        async with self.session_maker() as session:
            stmt = (
                select(User)
                .join(DesignersTeamMembers, DesignersTeamMembers.designer_id == User.id)
                .where(DesignersTeamMembers.team_id.in_(team_id))
            )
            result = await session.scalars(stmt)
            return result.all()

    async def create_operational_task(self, task_info: CreateOperationDesignerTaskSchema, user: User):
        async with self.session_maker() as db:
            if task_info.assigned_to_id and not task_info.difficulty_ids:
                raise HTTPException(status_code=409, detail="Task cannot be assigned without difficulty")

            user_task_count_stmt = await db.execute(
                select(func.count()).select_from(DesignerTask).where(DesignerTask.created_by_id == user.id)
            )
            user_task_count = user_task_count_stmt.scalar() or 0
            task_sequence_number = user_task_count + 1

            stmt = (
                insert(DesignerTask)
                .values(
                    description=task_info.description,
                    created_by_id=user.id,
                    task_type=task_info.task_type,
                    assigned_to_id=task_info.assigned_to_id if task_info.assigned_to_id else None,
                    task_status=DesignerTaskStatus.WAITING_TO_START
                    if task_info.assigned_to_id
                    else DesignerTaskStatus.WAITING_TO_ASSIGN,
                    deadline=task_info.deadline,
                    is_high_priority=task_info.is_high_priority,
                    title=f"o.{task_sequence_number}",
                    is_operational=True,
                )
                .returning(DesignerTask.id)
            )

            result = await db.execute(stmt)
            task_id = result.scalar_one_or_none()

            if not task_id:
                raise HTTPException(status_code=400, detail="Task creation failed")

            if task_info.difficulty_ids:
                difficulty_ids = [item.id for item in task_info.difficulty_ids if item.id is not None]
                if difficulty_ids:
                    await db.execute(
                        insert(DesignerTaskDifficulty),
                        [{"task_id": task_id, "difficulty_id": diff_id} for diff_id in difficulty_ids],
                    )

            await db.commit()

            return await get_task(db=db, task_id=task_id, user=user)
