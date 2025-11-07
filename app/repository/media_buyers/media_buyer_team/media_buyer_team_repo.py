from collections import defaultdict
from datetime import date
from typing import List, Sequence

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, case, func, not_, or_, select
from sqlalchemy.orm import selectinload

from app.models import (
    Designer,
    DesignerTask,
    MediaBuyer,
    MediaBuyersTeam,
    MediaBuyersTeamMembers,
    User,
    WebMaster,
    WebMasterTask,
)
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.media_buyer_team.base import MediaBuyerTeamBaseRepository
from app.repository.utils import get_task_stats
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_status import DesignerTaskStatus, WebMasterTaskStatus
from app.schemas.media_buyer import MediaBuyerStatisticsSchema

logger = structlog.get_logger()


class MediaBuyerTeamRepository(MediaBuyerTeamBaseRepository, DatabaseEngineRepository):
    async def get_media_buyer_teams(
        self,
        user: User,
        limit: int,
        offset: int,
        vertical: VerticalType | None = None,
    ) -> Sequence[MediaBuyersTeam]:
        async with self.session_maker() as db:
            stmt = (
                select(MediaBuyersTeam)
                .where(not_(MediaBuyersTeam.is_deleted))
                .options(
                    selectinload(MediaBuyersTeam.responsible_designer_info).selectinload(Designer.user),
                    selectinload(MediaBuyersTeam.responsible_web_master_info).selectinload(WebMaster.user),
                    selectinload(MediaBuyersTeam.lead).selectinload(MediaBuyer.user),
                    selectinload(MediaBuyersTeam.members).selectinload(MediaBuyer.user),
                )
                .order_by(
                    MediaBuyersTeam.vertical.asc(),
                    MediaBuyersTeam.name.asc(),
                    MediaBuyersTeam.id.asc(),
                )
                .limit(limit)
                .offset(offset)
            )

            if vertical:
                stmt = stmt.where(MediaBuyersTeam.vertical == vertical)

            result = await db.execute(stmt)
            return result.scalars().all()

    async def get_total_teams(self, vertical: VerticalType | None = None) -> int:
        async with self.session_maker() as db:
            stmt = select(func.count()).select_from(MediaBuyersTeam).where(not_(MediaBuyersTeam.is_deleted))

            if vertical:
                stmt = stmt.where(MediaBuyersTeam.vertical == vertical)

            result = await db.execute(stmt)
            return result.scalar()

    async def get_media_buyer_team(
        self,
        team_id: int,
    ) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            stmt = (
                select(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id)
                .where(not_(MediaBuyersTeam.is_deleted))
                .options(
                    selectinload(MediaBuyersTeam.responsible_designer_info).selectinload(Designer.user),
                    selectinload(MediaBuyersTeam.responsible_web_master_info).selectinload(WebMaster.user),
                    selectinload(MediaBuyersTeam.lead).selectinload(MediaBuyer.user),
                    selectinload(MediaBuyersTeam.members).selectinload(MediaBuyer.user),
                )
            )

            if team := await db.scalar(stmt):
                return team

        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    async def get_media_buyer_teams_task_counts(
        self, team_id: int | None = None, vertical: list[VerticalType] | None = None
    ):
        async with self.session_maker() as db:
            statuses = [
                status
                for status in DesignerTaskStatus
                if status not in [DesignerTaskStatus.DRAFT, DesignerTaskStatus.COMPLETED]
            ]

            case_statements = [
                func.coalesce(func.count(case((DesignerTask.task_status == status, 1))), 0).label(status.value)
                for status in statuses
            ]

            stmt = (
                select(
                    MediaBuyersTeam.id.label("team_id"),
                    MediaBuyersTeam.name.label("team_name"),
                    MediaBuyersTeam.vertical,
                    *case_statements,
                )
                .outerjoin(
                    DesignerTask,
                    and_(
                        DesignerTask.buyer_team_id == MediaBuyersTeam.id,
                        DesignerTask.task_status.in_(statuses),
                        DesignerTask.is_deleted.is_(False),
                    ),
                )
                .group_by(MediaBuyersTeam.id, MediaBuyersTeam.name, MediaBuyersTeam.vertical)
                .having(or_(not_(MediaBuyersTeam.is_deleted), func.count(DesignerTask.id) > 0))
                .order_by(MediaBuyersTeam.name)
            )

            if team_id is not None:
                stmt = stmt.where(MediaBuyersTeam.id == team_id)

            if vertical:
                stmt = stmt.where(MediaBuyersTeam.vertical.in_(vertical))

            result = await db.execute(stmt)
            rows = result.mappings().all()

            grouped = defaultdict(list)
            for row in rows:
                team_data = {
                    "team_id": row["team_id"],
                    "team_name": row["team_name"],
                    "vertical": row["vertical"],
                    **{status: row.get(status, 0) for status in [s.value for s in statuses]},
                }
                grouped[row["vertical"]].append(team_data)

            return [{"vertical": v, "teams": t} for v, t in sorted(grouped.items())]

    async def get_total_buyers(self, team_id: int | None = None) -> int:
        async with self.session_maker() as db:
            stmt = select(func.count(MediaBuyer.id))
            if team_id:
                stmt = stmt.join(MediaBuyersTeamMembers).where(MediaBuyersTeamMembers.team_id == team_id)
            result = await db.execute(stmt)
            return result.scalar_one()

    async def get_buyer_statistics(
        self,
        team_id: int | None = None,
        vertical: list[VerticalType] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[MediaBuyerStatisticsSchema]:
        async with self.session_maker() as db:
            designer_stats = await get_task_stats(
                db,
                DesignerTask,
                DesignerTaskStatus,
                team_id,
                vertical,
                start_date,
                end_date,
                limit,
                offset,
                include_user_info=True,
            )
            webmaster_stats = await get_task_stats(
                db,
                WebMasterTask,
                WebMasterTaskStatus,
                team_id,
                vertical,
                start_date,
                end_date,
                limit,
                offset,
                include_user_info=False,
            )
            return MediaBuyerStatisticsSchema.from_stats(designer_stats, webmaster_stats)
