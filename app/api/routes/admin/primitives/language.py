from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependecies.auth import AuthenticateAdmin, AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import LanguageCreateSchema, LanguageResponseSchema

admin_language_router = APIRouter(prefix="/admin/languages", tags=["Admin"])


@admin_language_router.get("/all", response_model=list[LanguageResponseSchema])
async def get_all_languages(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.admin_primitives.get_all_languages()


@admin_language_router.post("/create", response_model=LanguageResponseSchema)
async def create_language(
    payload: LanguageCreateSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_primitives.create_language(payload.name, payload.code)


@admin_language_router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_language(
    language_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user=Depends(AuthenticateAdmin()),
):
    await db_repo.admin_primitives.delete_language(language_id)
