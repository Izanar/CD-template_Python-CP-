from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependecies.auth import AuthenticateAdmin, AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import PrimitiveCreateSchema, PrimitiveResponseSchema

admin_funnel_router = APIRouter(prefix="/admin/funnels", tags=["Admin"])


@admin_funnel_router.get("/all", response_model=list[PrimitiveResponseSchema])
async def get_all_funnels(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    context: Literal["create", "filter"] = Query("create", description="Create for task creation, filter for filters"),
    current_user=Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.admin_primitives.get_all_funnels(context=context)


@admin_funnel_router.post("/create", response_model=PrimitiveResponseSchema)
async def create_funnel(
    payload: PrimitiveCreateSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_primitives.create_funnel(payload.name)


@admin_funnel_router.delete("/{funnel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_funnel(
    funnel_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    await db_repo.admin_primitives.delete_funnel(funnel_id)
