from datetime import datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.config import ConfigDTO
from app.dependecies.stub import AppConfigStub, DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.user import RefreshTokenRequest, Token, User, UserResponseSchema

logger = structlog.get_logger()

auth_router = APIRouter(
    tags=["Auth"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(db_repo, username: str, password: str) -> bool | User:
    user = await db_repo.user.get_current_user(username=username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    user.allow_view_team_tasks = getattr(user.media_buyer, "allow_view_team_tasks", None)

    user.vertical = (
        getattr(user.media_buyer.teams[0], "vertical", None) if user.media_buyer and user.media_buyer.teams else None
    )

    return user


def create_token(data: dict, secret_key: str, algorithm: str, expires_delta: timedelta, jwt_version: int) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "jwt_version": jwt_version})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


async def decode_token(db_repo: DatabaseRepository, token: str, secret_key: str, algorithm: str) -> str:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username = payload.get("sub")
        token_jwt_version = payload.get("jwt_version")
        if not username or token_jwt_version is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await db_repo.user.get_current_user(username=username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token_jwt_version != user.jwt_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@auth_router.post("/api/token", response_model=Token)
async def login_for_access_token(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    config: ConfigDTO = Depends(AppConfigStub),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await authenticate_user(db_repo, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=config.jwt_token.expire_minutes),
        secret_key=config.jwt_token.secret_key,
        algorithm=config.jwt_token.algorithm,
        jwt_version=user.jwt_version,
    )
    refresh_token = create_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=config.jwt_token.refresh_expire_days),
        secret_key=config.jwt_token.secret_key,
        algorithm=config.jwt_token.algorithm,
        jwt_version=user.jwt_version,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponseSchema.model_validate(user),
        token_type="bearer",  # noqa: S106
    )


@auth_router.post("/api/token/refresh", response_model=Token)
async def refresh_access_token(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    token_request: RefreshTokenRequest,
    config: ConfigDTO = Depends(AppConfigStub),
):
    username = await decode_token(
        db_repo=db_repo,
        token=token_request.refresh_token,
        secret_key=config.jwt_token.secret_key,
        algorithm=config.jwt_token.algorithm,
    )

    user = await db_repo.user.get_current_user(username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=config.jwt_token.expire_minutes),
        secret_key=config.jwt_token.secret_key,
        algorithm=config.jwt_token.algorithm,
        jwt_version=user.jwt_version,
    )

    return Token(
        access_token=new_access_token,
        refresh_token=token_request.refresh_token,
        user=UserResponseSchema.model_validate(user),
        token_type="bearer",  # noqa: S106
    )
