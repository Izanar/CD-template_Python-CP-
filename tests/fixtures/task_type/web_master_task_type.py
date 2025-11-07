import uuid

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def new_web_master_task_type(admin_user, client: AsyncClient) -> int:
    unique_name = f"test_task_type_{uuid.uuid4().hex}"
    headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
    resp = await client.post(
        "/admin/web_master/tasks/create_type",
        json={"name": unique_name},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()["id"]
