# ruff: noqa: SIM105,S110
import uuid
from typing import Any, Callable

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repository.database.base import DatabaseRepository
from app.schemas.enums.user import UserRole
from app.schemas.user import UserCreateSchema


@pytest_asyncio.fixture(scope="session")
async def admin_credentials(engine):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    db_repo = DatabaseRepository.create(session_maker)
    try:
        await db_repo.user.create_user(
            UserCreateSchema(
                username="admin",
                password="password",  # noqa: S106
                role="admin",
            )
        )
    except Exception:
        pass
    return {"username": "admin", "password": "password"}


@pytest.fixture(scope="session")
def get_token(client: AsyncClient):
    async def _get(username: str, password: str) -> str:
        resp = await client.post(
            "/api/token",
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": "string",
                "client_secret": "string",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _get


@pytest.fixture(scope="session")
def make_user(client: AsyncClient, get_token, admin_credentials):
    async def _create(
        role: UserRole | str,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        role_str = role.value if isinstance(role, UserRole) else role
        username = username or f"autotest_{role_str}_{uuid.uuid4().hex[:6]}"
        password = password or "password"

        admin_token = await get_token(**admin_credentials)
        resp = await client.post(
            "/admin/user/create",
            json={
                "role": role_str,
                "username": username,
                "password": password,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if resp.status_code == 400 and "already in use" in resp.text:
            at = await get_token(username, password)
            return {
                "username": username,
                "role": role_str,
                "password": password,
                "access_token": at,
            }

        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        data.update(
            password=password,
            access_token=await get_token(username, password),
        )
        return data

    return _create


@pytest_asyncio.fixture(scope="session")
async def designer_user(make_user):
    return await make_user(UserRole.designer)


@pytest_asyncio.fixture(scope="session")
async def media_buyer_user(make_user):
    return await make_user(UserRole.media_buyer)


@pytest_asyncio.fixture(scope="session")
async def web_master_user(make_user):
    return await make_user(UserRole.web_master)


@pytest_asyncio.fixture(scope="session")
async def lead_web_master_user(make_user):
    return await make_user(UserRole.lead_web_master)


@pytest_asyncio.fixture(scope="session")
async def lead_media_buyer_user(make_user):
    return await make_user(UserRole.lead_media_buyer)


@pytest_asyncio.fixture(scope="session")
async def lead_designer_user(make_user):
    return await make_user(UserRole.lead_designer)


@pytest_asyncio.fixture(scope="session")
async def basic_user(make_user):
    return await make_user(UserRole.user)


@pytest_asyncio.fixture(scope="session")
async def admin_user(make_user):
    return await make_user(UserRole.admin)


TEST_ROLES = (
    UserRole.designer,
    UserRole.media_buyer,
    UserRole.web_master,
    UserRole.lead_web_master,
    UserRole.lead_media_buyer,
    UserRole.lead_designer,
    UserRole.admin,
)


@pytest_asyncio.fixture(scope="session")
async def restricted_users(make_user) -> Callable[..., list[tuple[UserRole, dict]]]:
    users = {role: await make_user(role) for role in TEST_ROLES}

    def get_users_except(*roles_to_exclude: UserRole) -> list[tuple[UserRole, dict]]:
        return [(role, user) for role, user in users.items() if role not in roles_to_exclude]

    return get_users_except
