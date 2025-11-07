from fastapi import HTTPException
from sqlalchemy import select

from app.models import DesignersTeam


async def get_team_by_id(db, team_id: int):
    if team := await db.scalar(select(DesignersTeam).where(DesignersTeam.id == team_id)):
        return team

    raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")
