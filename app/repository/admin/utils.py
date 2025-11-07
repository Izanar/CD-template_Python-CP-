from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Language


async def check_language_conflicts(session: AsyncSession, name: str, code: str) -> Language | None:
    code_lower = code.lower()
    name_lower = name.lower()

    stmt = select(Language).where(func.lower(Language.code) == code_lower)
    existing_by_code = await session.scalar(stmt)

    if existing_by_code:
        if existing_by_code.is_deleted:
            existing_by_code.is_deleted = False
            existing_by_code.name = name
            existing_by_code.code = code
            await session.commit()
            await session.refresh(existing_by_code)
            return existing_by_code
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language with this code already exists",
        )

    stmt = select(Language).where(func.lower(Language.name) == name_lower)
    existing_by_name = await session.scalar(stmt)

    if existing_by_name:
        if existing_by_name.is_deleted:
            existing_by_name.is_deleted = False
            existing_by_name.name = name
            existing_by_name.code = code
            await session.commit()
            await session.refresh(existing_by_name)
            return existing_by_name
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language with this name already exists",
        )

    return None
