from datetime import date, datetime, time

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, insert, select, update

from app.models import (
    User,
    WebMasterDifficultyLevel,
    WebMastersTeam,
    WebMastersTeamMembers,
    WebMasterTask,
    WebMasterTaskDifficulty,
)
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.web_masters.lead_web_master.base import LeadWebMasterBaseRepository
from app.repository.web_masters.lead_web_master.utils import get_user
from app.repository.web_masters.web_master.utils import get_task
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.enums.user import UserRole
from app.schemas.media_buyers.tasks.web_master_tasks import UpdateWebMasterTaskSchema


class LeadWebMasterRepository(LeadWebMasterBaseRepository, DatabaseEngineRepository):
    async def get_completed_tasks(
        self,
        user_id: int | None,
        team_id: int | None,
        start_date: date,
        end_date: date,
        task_status: WebMasterTaskStatus,
    ):
        async with self.session_maker() as db:
            filters = [
                WebMasterTask.task_status == task_status,
                WebMasterTask.completed_at >= datetime.combine(start_date, time.min),
                WebMasterTask.completed_at <= datetime.combine(end_date, time.max),
            ]

            if user_id is not None:
                filters.append(WebMasterTask.assigned_to_id == user_id)

            if team_id is not None:
                filters.append(
                    WebMasterTask.assigned_to_id.in_(
                        select(WebMastersTeamMembers.web_master_id).where(WebMastersTeamMembers.team_id == team_id)
                    )
                )

            stmt = (
                select(
                    WebMasterTask.assigned_to_id.label("user_id"),
                    func.count(func.distinct(WebMasterTask.id)).label("completed_tasks"),
                    (func.coalesce(func.sum(func.distinct(WebMasterDifficultyLevel.points)), 0)).label("total_points"),
                )
                .select_from(WebMasterTask)
                .outerjoin(WebMasterTask, WebMasterTask.difficulties)
                .where(and_(*filters))
                .group_by(WebMasterTask.assigned_to_id)
            )

            result = await db.execute(stmt)
            return result.all()

    async def update_web_master_task(self, task_info: UpdateWebMasterTaskSchema, user: User):
        async with self.session_maker() as db:
            existing_task = await get_task(db=db, task_id=task_info.task_id, user=user)
            if not existing_task:
                raise HTTPException(status_code=404, detail="Task not found")

            update_data = task_info.dict(exclude_unset=True, exclude={"task_id", "difficulty_ids"})

            if task_info.assigned_to_id is not None and task_info.assigned_to_id != existing_task.assigned_to_id:
                if existing_task.task_status in (WebMasterTaskStatus.COMPLETED, WebMasterTaskStatus.UNDER_BUYER_REVIEW):
                    raise HTTPException(
                        status_code=409,
                        detail="Web master can`t be assigned when task status is 'COMPLETED' or 'UNDER_BUYER_REVIEW'",
                    )

                has_difficulty = bool(task_info.difficulty_ids or existing_task.difficulties)

                if not has_difficulty:
                    raise HTTPException(status_code=409, detail="Task cannot be assigned without difficulty")

                await get_user(db=db, user_id=task_info.assigned_to_id)
                update_data["assigned_to_id"] = task_info.assigned_to_id

            if task_info.assigned_to_id is not None and task_info.assigned_to_id != existing_task.assigned_to_id:
                update_data["task_status"] = WebMasterTaskStatus.WAITING_TO_START

            if update_data:
                await db.execute(
                    update(WebMasterTask).where(WebMasterTask.id == task_info.task_id).values(**update_data)
                )

            if task_info.difficulty_ids is not None:
                await db.execute(
                    delete(WebMasterTaskDifficulty).where(WebMasterTaskDifficulty.task_id == task_info.task_id)
                )

                difficulty_ids = [item.id for item in task_info.difficulty_ids if item.id is not None]
                if difficulty_ids:
                    await db.execute(
                        insert(WebMasterTaskDifficulty),
                        [{"task_id": task_info.task_id, "difficulty_id": diff_id} for diff_id in difficulty_ids],
                    )

            await db.commit()
            db.expire(existing_task, ["difficulties"])

            return await get_task(db=db, task_id=task_info.task_id, user=user)

    async def view_web_master_load(self, is_my_teams: bool, user_id: int):
        async with self.session_maker() as db:
            task_count_subquery = (
                select(
                    WebMasterTask.assigned_to_id,
                    func.count(WebMasterTask.id).label("assigned_tasks_count"),
                )
                .group_by(WebMasterTask.assigned_to_id)
                .subquery()
            )

            stmt = (
                select(User, task_count_subquery.c.assigned_tasks_count)
                .where(User.role == UserRole.web_master)
                .outerjoin(task_count_subquery, task_count_subquery.c.assigned_to_id == User.id)
            )

            if is_my_teams:
                team_members_stmt = (
                    select(WebMastersTeamMembers.web_master_id)
                    .join(WebMastersTeam, WebMastersTeam.id == WebMastersTeamMembers.team_id)
                    .where(WebMastersTeam.lead_id == user_id)
                )

                team_members_ids = await db.scalars(team_members_stmt)
                team_members_ids = list(team_members_ids)

                stmt = stmt.where(User.id.in_(team_members_ids))

            result = await db.execute(stmt)
            web_masters = []

            for user, assigned_tasks_count in result.all():
                web_masters.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "created_at": user.created_at,
                        "role": user.role,
                        "assigned_tasks_count": assigned_tasks_count or 0,
                    }
                )

            return web_masters

    async def get_web_masters_by_team(self, team_id: int) -> list[User]:
        async with self.session_maker() as session:
            stmt = (
                select(User)
                .join(WebMastersTeamMembers, WebMastersTeamMembers.web_master_id == User.id)
                .where(WebMastersTeamMembers.team_id == team_id)
            )
            result = await session.scalars(stmt)
            return result.all()
