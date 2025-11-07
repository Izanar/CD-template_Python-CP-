from fastapi import Depends

from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.services.notifications import NotificationService


def get_notification_service(
    db_repo: DatabaseRepository = Depends(DatabaseRepositoryStub),
) -> NotificationService:
    return NotificationService(db_repo)
