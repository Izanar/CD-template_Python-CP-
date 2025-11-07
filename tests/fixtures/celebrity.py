import uuid

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def celebrity_1(admin_user, client: AsyncClient) -> dict:
    unique_id = str(uuid.uuid4())[:8]
    headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
    resp = await client.post(
        "/admin/celebrities/create",
        json={"name": f"Test Celebrity 1 {unique_id}"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def celebrity_2(admin_user, client: AsyncClient) -> dict:
    unique_id = str(uuid.uuid4())[:8]
    headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
    resp = await client.post(
        "/admin/celebrities/create",
        json={"name": f"Test Celebrity 2 {unique_id}"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def celebrity_3(admin_user, client: AsyncClient) -> dict:
    unique_id = str(uuid.uuid4())[:8]
    headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
    resp = await client.post(
        "/admin/celebrities/create",
        json={"name": f"Test Celebrity 3 {unique_id}"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()
