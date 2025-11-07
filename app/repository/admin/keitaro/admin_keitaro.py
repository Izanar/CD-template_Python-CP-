from typing import List

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.models import KeitaroConfig
from app.repository.admin.teams.media_buyer_team.utils import check_team_by_id
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.keitaro_admin import (
    AddKeitaroConfigToTeamResponseSchema,
    KeitaroConfigCreateSchema,
    KeitaroConfigResponseSchema,
    KeitaroConfigUpdateSchema,
)


class AdminKeitaroRepository(DatabaseEngineRepository):
    async def create_config(self, config_info: KeitaroConfigCreateSchema) -> KeitaroConfig:
        async with self.session_maker() as db:
            config = KeitaroConfig(
                name=config_info.name,
                api_key=config_info.api_key,
                base_url=config_info.base_url,
                creo=config_info.creo,
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
            return config

    async def list_configs(self) -> List[KeitaroConfigResponseSchema]:
        async with self.session_maker() as db:
            query = select(
                KeitaroConfig.id,
                KeitaroConfig.name,
                KeitaroConfig.base_url,
                KeitaroConfig.creo,
                KeitaroConfig.created_at,
                KeitaroConfig.is_active,
            ).where(KeitaroConfig.is_active)
            result = await db.execute(query)
            rows = result.all()

            return [KeitaroConfigResponseSchema(**row._asdict()) for row in rows]

    async def get_config(self, config_id: int) -> KeitaroConfigResponseSchema:
        async with self.session_maker() as db:
            query = select(
                KeitaroConfig.id,
                KeitaroConfig.name,
                KeitaroConfig.base_url,
                KeitaroConfig.creo,
                KeitaroConfig.created_at,
                KeitaroConfig.is_active,
            ).where(KeitaroConfig.id == config_id)
            result = await db.execute(query)
            row = result.first()

            if not row:
                raise HTTPException(status_code=404, detail=f"Keitaro config with id {config_id} not found")

            return KeitaroConfigResponseSchema(**row._asdict())

    async def add_config_to_team(self, team_id: int, keitaro_config_id: int) -> AddKeitaroConfigToTeamResponseSchema:
        async with self.session_maker() as db:
            team = await check_team_by_id(db, team_id)
            config_response = await self.get_config(keitaro_config_id)

            team.keitaro_config_id = keitaro_config_id
            await db.commit()
            await db.refresh(team)

            return AddKeitaroConfigToTeamResponseSchema(config=config_response, team=team)

    async def update_config(
        self, config_id: int, update_data: KeitaroConfigUpdateSchema
    ) -> KeitaroConfigResponseSchema:
        async with self.session_maker() as db:
            config = await db.scalar(select(KeitaroConfig).where(KeitaroConfig.id == config_id))
            if not config:
                raise HTTPException(status_code=404, detail=f"Keitaro config with id {config_id} not found")

            if update_data.name is not None:
                config.name = update_data.name
            if update_data.api_key is not None:
                config.api_key = update_data.api_key
            if update_data.base_url is not None:
                config.base_url = update_data.base_url
            if update_data.creo is not None:
                config.creo = update_data.creo

            await db.commit()
            await db.refresh(config)

            return KeitaroConfigResponseSchema(
                id=config.id,
                name=config.name,
                base_url=config.base_url,
                creo=config.creo,
                created_at=config.created_at,
                is_active=config.is_active,
            )

    async def delete_config(self, config_id: int) -> None:
        await self.get_config(config_id)

        async with self.session_maker() as db:
            await db.execute(delete(KeitaroConfig).where(KeitaroConfig.id == config_id))
            await db.commit()
