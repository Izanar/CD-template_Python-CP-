import pytest_asyncio
from httpx import AsyncClient

from app.schemas.enums.task_status import WebMasterTaskStatus


@pytest_asyncio.fixture
async def new_draft_web_master_task(
    client: AsyncClient,
    media_buyer_user,
    media_buyer_team_with_member,
    new_web_master_task_type,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    resp = await client.post(
        "/media_buyer/web_master/create_draft",
        json={"description": "to-send", "task_type_id": new_web_master_task_type},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def new_web_master_task(
    client: AsyncClient,
    media_buyer_user,
    media_buyer_team_with_member,
    new_web_master_task_type,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    resp = await client.post(
        "/media_buyer/web_master/create",
        json={"description": "not-a-draft", "task_type_id": new_web_master_task_type},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def new_web_master_task_under_review(
    client: AsyncClient,
    new_web_master_task: dict,
    lead_web_master_user: dict,
) -> dict:
    headers = {"Authorization": f"Bearer {lead_web_master_user['access_token']}"}
    resp = await client.post(
        f"/lead_web_master/task/{new_web_master_task['id']}/approve",
        headers=headers,
    )
    resp.raise_for_status()
    return {**new_web_master_task, "task_status": "UNDER_BUYER_REVIEW"}


@pytest_asyncio.fixture
async def unsolved_web_master_edit(
    client: AsyncClient,
    media_buyer_user: dict,
    web_master_user: dict,
    lead_web_master_user: dict,
    new_web_master_task_under_review: dict,
) -> int:
    task_id = new_web_master_task_under_review["id"]
    buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

    resp = await client.post(
        f"/media_buyer/web_master/request_task_edit/{task_id}",
        json={"description": "please adjust layout"},
        headers=buyer_headers,
    )
    resp.raise_for_status()
    edit_id = resp.json()["edits"][0]["id"]

    wm_headers = {"Authorization": f"Bearer {web_master_user['access_token']}"}
    await client.post(f"/web_master/start_task/{task_id}", headers=wm_headers)
    await client.post(f"/web_master/mark_task_as_done/{task_id}", headers=wm_headers)

    lead_headers = {"Authorization": f"Bearer {lead_web_master_user['access_token']}"}
    await client.post(f"/lead_web_master/task/{task_id}/approve", headers=lead_headers)

    return edit_id


@pytest_asyncio.fixture
async def web_master_task_waiting_to_start(
    client: AsyncClient,
    new_web_master_task: dict,
    new_web_master_task_difficulty,
    lead_web_master_user: dict,
    web_master_user: dict,
) -> dict:
    task_id = new_web_master_task["id"]

    diff_id = (await new_web_master_task_difficulty())["id"]

    headers_lead = {"Authorization": f"Bearer {lead_web_master_user['access_token']}"}
    resp = await client.patch(
        "/lead_web_master/task/update",
        json={
            "task_id": task_id,
            "assigned_to_id": web_master_user["id"],
            "difficulty_ids": [{"id": diff_id}],
        },
        headers=headers_lead,
    )
    resp.raise_for_status()

    return {
        **new_web_master_task,
        "task_status": WebMasterTaskStatus.WAITING_TO_START.value,
        "assigned_to_id": web_master_user["id"],
    }


@pytest_asyncio.fixture
async def web_master_task_in_progress(
    client: AsyncClient,
    web_master_task_waiting_to_start: dict,
    web_master_user: dict,
) -> dict:
    task_id = web_master_task_waiting_to_start["id"]
    headers_designer = {"Authorization": f"Bearer {web_master_user['access_token']}"}

    resp = await client.post(f"/web_master/start_task/{task_id}", headers=headers_designer)
    resp.raise_for_status()

    return resp.json()
