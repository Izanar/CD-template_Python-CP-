from datetime import date
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.enums.user import UserRole
from app.schemas.message import MessageSchema
from app.schemas.pagination import PaginationResponse
from app.schemas.user import (
    FullUserResponseSchema,
    LogoutRequest,
    UserCreateSchema,
    UserResponseSchema,
    UserUpdateSchema,
)

admin_router = APIRouter(
    prefix="/admin/user",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_router.post("/create", response_model=UserResponseSchema)
async def create_user(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    user: UserCreateSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.create_user(user=user)


@admin_router.get("/all", response_model=PaginationResponse[FullUserResponseSchema])
async def get_all_users(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    limit: int = Query(10, ge=1, le=1000, description="Limit of users per page"),
    offset: int = Query(0, ge=0, description="Offset of users"),
    role: UserRole | None = Query(None, description="Filter users by role"),
    has_team: bool | None = Query(None, description="Filter users with team"),
    username: str | None = Query(None, description="Filter users by username"),
    order_by: str | None = Query(None, description="Order by"),
    order_direction: Literal["asc", "desc"] | None = Query("desc", description="Order direction"),
    created_at: date | None = Query(None, description="Created at date"),
    team_id: int | None = Query(None, description="Filter users by team ID"),
    media_buyer_team_id: int | None = Query(None, description="Filter users by team ID"),
):
    users, total = await db_repo.user.get_all_users(
        limit=limit,
        offset=offset,
        role=role,
        has_team=has_team,
        order_by=order_by,
        order_direction=order_direction,
        created_at=created_at,
        team_id=team_id,
        media_buyer_team_id=media_buyer_team_id,
        username=username,
    )

    users_schema = [FullUserResponseSchema(user=user) for user in users]

    return PaginationResponse.create(items=users_schema, total=total, limit=limit, offset=offset)


@admin_router.get("/{user_id}", response_model=UserResponseSchema)
async def get_user(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    user_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.get_user(user_id=user_id)


@admin_router.patch("/{user_id}", response_model=UserResponseSchema)
async def update_user(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    user: UserUpdateSchema,
    user_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.update_user(user=user, user_id=user_id)


@admin_router.delete("/{user_id}", response_model=UserResponseSchema)
async def delete_user(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    user_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.user.delete_user(user_id=user_id)


@admin_router.post("/logout", response_model=MessageSchema)
async def logout_user(
    request: LogoutRequest,
    db_repo: DatabaseRepository = Depends(DatabaseRepositoryStub),
    current_user: User = Depends(AuthenticateAdmin()),
):
    await db_repo.user.logout_user(user_id=request.user_id)
    return MessageSchema(message="User has been logged out")


@admin_router.post("/logout/all", response_model=MessageSchema)
async def logout_all_users(
    db_repo: DatabaseRepository = Depends(DatabaseRepositoryStub),
    current_user: User = Depends(AuthenticateAdmin()),
):
    await db_repo.user.logout_all_users()
    return MessageSchema(message="All users have been logged out")
