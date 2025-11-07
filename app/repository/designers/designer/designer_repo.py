from datetime import datetime, time, timezone
from typing import Literal

import structlog
from fastapi import HTTPException
from sqlalchemy import Numeric, case, cast, func, select, update
from sqlalchemy.orm import selectinload

from app.models import Designer, DesignerTask, DifficultyLevel, TaskEvaluation, User
from app.repository.designers.designer.base import DesignerBaseRepository
from app.repository.designers.designer.utils import (
    build_task_filters,
    check_task_ready_for_review,
    filter_by_team_id,
    get_task,
    handle_task_evaluation,
    validate_date_range,
)
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.enums.task_status import (
    DesignerTaskStatus,
)
from app.schemas.enums.user import UserRole

logger = structlog.get_logger(__name__)


class DesignerRepository(DesignerBaseRepository, DatabaseEngineRepository):
    async def update_task_status(
        self,
        task_id: int,
        task_status: DesignerTaskStatus,
        current_user: User,
        rating: int | None = None,
        comment: str | None = None,
    ):
        async with self.session_maker() as db:
            existing_task = await get_task(db=db, task_id=task_id, user=current_user)

            if task_status == DesignerTaskStatus.UNDER_TL_REVIEW:
                await check_task_ready_for_review(existing_task)

            filters = await build_task_filters(current_user=current_user, task_id=task_id)

            update_values = {"task_status": task_status}

            if task_status == DesignerTaskStatus.COMPLETED:
                update_values["completed_at"] = datetime.now(timezone.utc)
                update_values["is_high_priority"] = False

                await handle_task_evaluation(
                    db=db,
                    task=existing_task,
                    current_user=current_user,
                    rating=rating,
                    comment=comment,
                )

            if (
                task_status == DesignerTaskStatus.UNDER_TL_REVIEW
                and current_user.role == UserRole.lead_designer
                and existing_task.assigned_to_id == current_user.id
            ):
                # Prevent operational tasks from going to buyer review
                if existing_task.is_operational:
                    update_values["task_status"] = DesignerTaskStatus.COMPLETED
                else:
                    update_values["task_status"] = DesignerTaskStatus.UNDER_BUYER_REVIEW

            stmt = update(DesignerTask).where(*filters).values(**update_values).returning(DesignerTask.id)

            result = await db.execute(stmt)
            updated_task_id = result.scalar_one_or_none()

            if not updated_task_id:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            await db.commit()
            await db.refresh(existing_task)
            return existing_task

    async def get_designers(self, team_id: list[int] | None = None):
        async with self.session_maker() as db:
            stmt = select(Designer).options(
                selectinload(Designer.assigned_tasks).selectinload(DesignerTask.created_by),
                selectinload(Designer.assigned_tasks),
                selectinload(Designer.user),
                selectinload(Designer.teams),
            )

            stmt = await filter_by_team_id(
                stmt=stmt,
                team_id=team_id,
            )

            result = await db.scalars(stmt)
            return result.all()

    async def get_designers_completion_stats(
        self,
        team_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        completed_from: datetime | None = None,
        completed_to: datetime | None = None,
        order_by: Literal["completed_tasks", "total_points", "mean_rating", "username"] = "total_points",
        order_direction: Literal["asc", "desc"] = "desc",
    ) -> list[tuple[Designer, int, int]]:
        validate_date_range(completed_from, completed_to, "completed_from", "completed_to")
        validate_date_range(created_from, created_to, "created_from", "created_to")

        created_from = datetime.combine(created_from, time.min) if created_from else None
        created_to = datetime.combine(created_to, time.max) if created_to else None
        completed_from = datetime.combine(completed_from, time.min) if completed_from else None
        completed_to = datetime.combine(completed_to, time.max) if completed_to else None

        filters = [DesignerTask.completed_at.isnot(None), DesignerTask.is_deleted == False]

        if created_from:
            filters.append(DesignerTask.created_at >= created_from)
        if created_to:
            filters.append(DesignerTask.created_at <= created_to)
        if completed_from:
            filters.append(DesignerTask.completed_at >= completed_from)
        if completed_to:
            filters.append(DesignerTask.completed_at <= completed_to)

        async with self.session_maker() as db:
            rating_subq = (
                select(
                    DesignerTask.assigned_to_id.label("designer_id"),
                    func.round(cast(func.avg(TaskEvaluation.rating), Numeric), 2).label("mean_rating"),
                )
                .join(DesignerTask, DesignerTask.id == TaskEvaluation.designer_task_id)
                .where(TaskEvaluation.rating.is_not(None), *filters)
                .group_by(DesignerTask.assigned_to_id)
                .subquery()
            )

            stmt = (
                select(
                    Designer,
                    func.count(DesignerTask.id).label("completed_tasks"),
                    func.coalesce(func.sum(DifficultyLevel.points), 0).label("total_points"),
                    rating_subq.c.mean_rating,
                )
                .join(DesignerTask, DesignerTask.assigned_to_id == Designer.id)
                .outerjoin(DifficultyLevel, DesignerTask.difficulties)
                .outerjoin(rating_subq, rating_subq.c.designer_id == Designer.id)
                .join(User, User.id == Designer.id)
                .where(*filters)
                .options(
                    selectinload(Designer.user),
                    selectinload(Designer.teams),
                )
                .group_by(Designer.id, rating_subq.c.mean_rating, User.username)
            )

            sort_map = {
                "completed_tasks": func.count(DesignerTask.id),
                "total_points": func.coalesce(func.sum(DifficultyLevel.points), 0),
                "mean_rating": rating_subq.c.mean_rating,
                "username": func.lower(User.username),
            }
            order_expr = sort_map[order_by]
            order_clause = (order_expr.desc() if order_direction == "desc" else order_expr.asc()).nulls_last()
            stmt = stmt.order_by(order_clause)

            stmt = await filter_by_team_id(stmt=stmt, team_id=team_id)
            result = await db.execute(stmt)
            return result.all()

    async def get_media_buyer_teams_task_counts(self):
        async with self.session_maker() as db:
            statuses = [
                status
                for status in DesignerTaskStatus
                if status not in [DesignerTaskStatus.DRAFT, DesignerTaskStatus.UNDER_BUYER_REVIEW]
            ]

            case_statements = {
                status.value: func.coalesce(func.sum(case((DesignerTask.task_status == status, 1), else_=0)), 0).label(
                    status.value
                )
                for status in statuses
            }

            stmt = select(*case_statements.values()).where(
                DesignerTask.task_status.in_(statuses), DesignerTask.is_operational.is_(True)
            )

            result = await db.execute(stmt)
            return result.mappings().first()
