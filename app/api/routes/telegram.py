from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.config.config import ConfigDTO
from app.dependecies.auth import AuthenticateUser
from app.dependecies.stub import AppConfigStub, DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.telegram import TelegramChatIDResponse

telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])


@telegram_router.get("/register", response_model=str)
async def get_telegram_register_link(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    config: ConfigDTO = Depends(AppConfigStub),
    current_user: User = Depends(AuthenticateUser()),
):
    token = await db_repo.telegram.set_telegram_token(current_user.id)
    return f"{config.telegram.link}{token}"


@telegram_router.delete(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from Telegram",
)
async def telegram_logout(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateUser()),
) -> Response:
    await db_repo.telegram.logout_user(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@telegram_router.get(
    "/user/chat_id",
    response_model=TelegramChatIDResponse,
    summary="Get Telegram chat ID for current user",
)
async def get_telegram_chat_id(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateUser()),
) -> TelegramChatIDResponse:
    chat_id = await db_repo.telegram.get_chat_id_by_user_id(current_user.id)
    return TelegramChatIDResponse(chat_id=chat_id)
