from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependecies.auth import AuthenticateAdmin, AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import CelebrityResponseSchema, PrimitiveCreateSchema

admin_celebrity_router = APIRouter(prefix="/admin/celebrities", tags=["Admin"])


@admin_celebrity_router.get("/all", response_model=list[CelebrityResponseSchema])
async def get_all_celebrities(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    context: Literal["create", "filter"] = Query(
        "create", description="Create для создания задач, filter для фильтров"
    ),
    current_user=Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.admin_primitives.get_all_celebrities(context=context)


@admin_celebrity_router.post("/create", response_model=CelebrityResponseSchema)
async def create_celebrity(
    payload: PrimitiveCreateSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_primitives.create_celebrity(payload.name)


@admin_celebrity_router.delete("/{celebrity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_celebrity(
    celebrity_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    await db_repo.admin_primitives.delete_celebrity(celebrity_id)
