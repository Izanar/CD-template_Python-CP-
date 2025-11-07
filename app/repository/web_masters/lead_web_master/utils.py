from fastapi import HTTPException
from sqlalchemy import select

from app.models import User


async def get_user(db, user_id: int):
    if user := await db.scalar(select(User).where(User.id == user_id)):
        return user
    raise HTTPException(status_code=400, detail="User does not exist")
