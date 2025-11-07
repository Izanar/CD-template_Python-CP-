from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependecies.auth import AuthenticateAdmin, AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import (  # Reuse for simplicity
    PrimitiveCreateSchema,
    PrimitiveResponseSchema,
)

admin_site_name_router = APIRouter(prefix="/admin/site_names", tags=["Admin"])


@admin_site_name_router.get("/all", response_model=list[PrimitiveResponseSchema])  # Adjust schema name if needed
async def get_all_site_names(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    context: Literal["create", "filter"] = Query("create", description="Create for task creation, filter for filters"),
    current_user=Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.admin_primitives.get_all_site_names(context=context)


@admin_site_name_router.post("/create", response_model=PrimitiveResponseSchema)  # Adjust schema name if needed
async def create_site_name(
    payload: PrimitiveCreateSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_primitives.create_site_name(payload.name)


@admin_site_name_router.delete("/{site_name_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site_name(
    site_name_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    await db_repo.admin_primitives.delete_site_name(site_name_id)
