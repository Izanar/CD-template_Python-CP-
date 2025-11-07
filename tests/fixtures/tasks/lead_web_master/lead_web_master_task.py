import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def new_task_under_review(client: AsyncClient, new_task, lead_web_master_user) -> dict:
    headers = {"Authorization": f"Bearer {lead_web_master_user['access_token']}"}
    resp = await client.post(f"/lead_web_master/task/{new_task['id']}/approve", headers=headers)
    resp.raise_for_status()
    return {**new_task, "task_status": "UNDER_BUYER_REVIEW"}
