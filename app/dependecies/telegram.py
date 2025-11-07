from fastapi import Depends

from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.services.telegram.bot import TelegramService


def get_telegram_service(db_repo: DatabaseRepository = Depends(DatabaseRepositoryStub)) -> TelegramService:
    return TelegramService(telegram_repo=db_repo.telegram)
