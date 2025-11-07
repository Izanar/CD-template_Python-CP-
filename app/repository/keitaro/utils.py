from typing import Optional

from fastapi import HTTPException

from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.enums.user import UserRole


async def resolve_keitaro_config_user(current_user: User, user_id: Optional[int], db_repo: DatabaseRepository) -> User:
    if user_id is not None:
        allowed_roles = (UserRole.admin, UserRole.media_buyer, UserRole.lead_media_buyer)
        if current_user.role in allowed_roles:
            target_user = await db_repo.user.get_user(user_id)
            if not target_user:
                raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
            return target_user
    return current_user


def resolve_user_id_for_creative(
    creative, user_id_from_request: Optional[int], current_user_id: int
) -> tuple[int, int]:
    if user_id_from_request is not None:
        user_id_to_save = user_id_from_request
    elif creative.keitaro_config_user_id is not None:
        user_id_to_save = creative.keitaro_config_user_id
    else:
        user_id_to_save = current_user_id

    return user_id_to_save, user_id_to_save


async def get_username_for_campaigns(user_id: int | None, keitaro_username: str, user_repo) -> str:
    if user_id is not None:
        user = await user_repo.get_user(user_id)
        return user.username
    return keitaro_username
