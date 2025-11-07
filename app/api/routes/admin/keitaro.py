from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.keitaro_admin import (
    AddKeitaroConfigToTeamResponseSchema,
    AddKeitaroConfigToTeamSchema,
    KeitaroConfigCreateSchema,
    KeitaroConfigResponseSchema,
    KeitaroConfigUpdateSchema,
)

admin_keitaro_router = APIRouter(
    prefix="/admin/keitaro",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_keitaro_router.post(
    "/config",
    response_model=KeitaroConfigResponseSchema,
    status_code=201,
)
async def create_keitaro_config(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    config: KeitaroConfigCreateSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_keitaro.create_config(config_info=config)


@admin_keitaro_router.get(
    "/config",
    response_model=list[KeitaroConfigResponseSchema],
    status_code=200,
)
async def list_keitaro_configs(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_keitaro.list_configs()


@admin_keitaro_router.get(
    "/config/{config_id}",
    response_model=KeitaroConfigResponseSchema,
    status_code=200,
)
async def get_keitaro_config(
    config_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_keitaro.get_config(config_id)


@admin_keitaro_router.post(
    "/config/add_to_team",
    response_model=AddKeitaroConfigToTeamResponseSchema,
    status_code=200,
)
async def add_keitaro_config_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddKeitaroConfigToTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_keitaro.add_config_to_team(
        team_id=data.team_id,
        keitaro_config_id=data.keitaro_config_id,
    )


@admin_keitaro_router.patch(
    "/config/{config_id}",
    response_model=KeitaroConfigResponseSchema,
    status_code=200,
)
async def update_keitaro_config(
    config_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    update_data: KeitaroConfigUpdateSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_keitaro.update_config(config_id, update_data)


@admin_keitaro_router.delete(
    "/config/{config_id}",
    status_code=204,
)
async def delete_keitaro_config(
    config_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    await db_repo.admin_keitaro.delete_config(config_id)
