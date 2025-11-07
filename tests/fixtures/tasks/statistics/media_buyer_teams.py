import uuid

import pytest_asyncio
from sqlalchemy import insert, text

from app.models import MediaBuyersTeam, MediaBuyersTeamMembers
from app.schemas.enums.user import UserRole


@pytest_asyncio.fixture
async def make_media_buyer_teams(engine, make_user):
    async def _builder(count: int = 1, *, add_member: bool = True) -> list[tuple[int, int | None]]:
        results: list[tuple[int, int | None]] = []

        for _ in range(count):
            async with engine.begin() as conn:
                team_id = await conn.scalar(
                    insert(MediaBuyersTeam)
                    .values(
                        name=f"team_{uuid.uuid4().hex[:8]}",
                        prefix=f"pref_{uuid.uuid4().hex[:4]}",
                    )
                    .returning(MediaBuyersTeam.id)
                )

            buyer_id: int | None = None
            if add_member:
                buyer = await make_user(UserRole.media_buyer)
                buyer_id = buyer["id"]

                async with engine.begin() as conn:
                    await conn.execute(
                        text("INSERT OR IGNORE INTO media_buyers (id) VALUES (:id)"),
                        {"id": buyer_id},
                    )

                async with engine.begin() as conn:
                    await conn.execute(insert(MediaBuyersTeamMembers).values(team_id=team_id, media_buyer_id=buyer_id))

            results.append((team_id, buyer_id))

        return results

    return _builder
