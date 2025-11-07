from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MediaBuyer, User


async def validate_assistant_assignment(db: AsyncSession, user_id: int, assistant_id: int) -> None:
    if assistant_id == user_id:
        raise HTTPException(status_code=400, detail="User cannot be their own assistant")

    existing_ids = await db.scalars(select(MediaBuyer.id).where(MediaBuyer.id.in_([user_id, assistant_id])))
    existing_ids_set = set(existing_ids)

    if user_id not in existing_ids_set:
        raise HTTPException(status_code=404, detail="User not found")
    if assistant_id not in existing_ids_set:
        raise HTTPException(status_code=404, detail="Assistant not found")


async def get_teacher_info(db: AsyncSession, user: User) -> tuple[int, str]:
    """Returns (teacher_id, teacher_username) or (user.id, user.username) if no teacher"""
    teacher_id = await db.scalar(select(MediaBuyer.assistant_reference_id).where(MediaBuyer.id == user.id))
    if teacher_id:
        teacher_username = await db.scalar(select(User.username).where(User.id == teacher_id))
        return teacher_id, teacher_username
    return user.id, user.username


async def get_keitaro_username_for_media_buyer(db: AsyncSession, user: User) -> str:
    _, username = await get_teacher_info(db, user)
    return username


async def get_keitaro_config_user_id(db: AsyncSession, user: User) -> int:
    user_id, _ = await get_teacher_info(db, user)
    return user_id
