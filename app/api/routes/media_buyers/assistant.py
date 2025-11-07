from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyer import SetAssistantSchema
from app.schemas.user import UserResponseSchema

assistant_router = APIRouter(
    prefix="/admin/media_buyer/assistant",
    tags=["Admin"],
)


@assistant_router.post(
    "/",
    response_model=UserResponseSchema,
    status_code=200,
)
async def set_assistant(
    assistant_data: SetAssistantSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.assistant.set_assistant(assistant_data)
