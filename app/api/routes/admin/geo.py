from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Query, status

from app.dependecies.auth import (
    AuthenticateAdmin,
    AuthenticatedDesignerTasksRoles,
)
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import GeoCreateSchema, GeoResponseSchema

admin_geo_router = APIRouter(
    prefix="/admin/geo",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_geo_router.get("/all", response_model=list[GeoResponseSchema])
async def get_all_geos(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    context: Literal["create", "filter"] = Query(
        "create",
        description="Create for task creation, filter for task creation. Creation default.",
    ),
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.user.get_all_geos(context=context)


@admin_geo_router.post("/create", response_model=GeoResponseSchema)
async def create_geo(
    payload: GeoCreateSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.create_geo(payload.code)


@admin_geo_router.delete("/{geo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_geo(
    geo_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.delete_geo(geo_id)
