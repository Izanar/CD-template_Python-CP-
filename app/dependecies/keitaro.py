from typing import Dict, Optional

from fastapi import Depends, Query

from app.dependecies.auth import AuthenticateMediaBuyerOrLead
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.keitaro.utils import resolve_keitaro_config_user
from app.services.keitaro.service import KeitaroService


async def get_keitaro_config(
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    user_id: Optional[int] = Query(None, description="User ID to get Keitaro config"),
    db_repo: DatabaseRepository = Depends(DatabaseRepositoryStub),
) -> Dict[str, str]:
    target_user = await resolve_keitaro_config_user(current_user, user_id, db_repo)
    return await db_repo.keitaro.get_user_keitaro_config(target_user)


def get_keitaro_service(keitaro_config: Dict[str, str] = Depends(get_keitaro_config)) -> KeitaroService:
    return KeitaroService(keitaro_config=keitaro_config)
