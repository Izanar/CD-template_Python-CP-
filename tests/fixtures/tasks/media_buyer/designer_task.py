import pytest_asyncio
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.task_type import DesignerTaskTypeEnum


@pytest_asyncio.fixture
async def new_draft_task(
    client: AsyncClient,
    media_buyer_user,
    media_buyer_team_with_member,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    resp = await client.post(
        "/media_buyer/designer/create_draft",
        json={"description": "to-send", "task_type": DesignerTaskTypeEnum.land_video.value},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def new_task(
    client: AsyncClient,
    media_buyer_user,
    media_buyer_team_with_member,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    resp = await client.post(
        "/media_buyer/designer/create",
        json={"description": "not-a-draft", "task_type": DesignerTaskTypeEnum.land_video.value},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def task_under_tl_review(
    client: AsyncClient,
    task_in_progress: dict,
    designer_file: tuple,
    designer_user: dict,
) -> dict:
    task_id, _file_id, headers_designer = designer_file
    resp = await client.post(
        f"/designer/mark_task_as_done/{task_id}",
        headers=headers_designer,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def new_task_under_review(
    client: AsyncClient,
    task_under_tl_review: dict,
    lead_designer_user: dict,
) -> dict:
    task_id = task_under_tl_review["id"]
    headers_lead = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
    resp = await client.post(
        f"/lead_designer/task/{task_id}/approve",
        headers=headers_lead,
    )
    resp.raise_for_status()
    return resp.json()


@pytest_asyncio.fixture
async def unsolved_edit(
    client: AsyncClient,
    media_buyer_user,
    designer_user,
    lead_designer_user,
    new_task_under_review,
) -> int:
    headers_buyer = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    resp = await client.post(
        f"/media_buyer/designer/request_task_edit/{new_task_under_review['id']}",
        json={"description": "fix colours"},
        headers=headers_buyer,
    )
    resp.raise_for_status()
    edit_id = resp.json()["edits"][0]["id"]

    headers_designer = {"Authorization": f"Bearer {designer_user['access_token']}"}
    resp = await client.post(
        f"/designer/start_task/{new_task_under_review['id']}",
        headers=headers_designer,
    )
    resp.raise_for_status()

    resp = await client.post(
        f"/designer/mark_task_as_done/{new_task_under_review['id']}",
        headers=headers_designer,
    )
    resp.raise_for_status()

    headers_lead = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
    resp = await client.post(
        f"/lead_designer/task/{new_task_under_review['id']}/approve",
        headers=headers_lead,
    )
    resp.raise_for_status()

    return edit_id


@pytest_asyncio.fixture
async def task_waiting_to_start(
    client: AsyncClient,
    new_task: dict,
    new_difficulty,
    lead_designer_user: dict,
    designer_user: dict,
) -> dict:
    task_id = new_task["id"]

    diff_id = (await new_difficulty())["id"]

    headers_lead = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
    await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": task_id,
            "assigned_to_id": designer_user["id"],
            "difficulty_ids": [{"id": diff_id}],
        },
        headers=headers_lead,
    )

    return {
        **new_task,
        "task_status": DesignerTaskStatus.WAITING_TO_START.value,
        "assigned_to_id": designer_user["id"],
    }


@pytest_asyncio.fixture
async def task_in_progress(
    client: AsyncClient,
    task_waiting_to_start: dict,
    designer_user: dict,
) -> dict:
    task_id = task_waiting_to_start["id"]
    headers_designer = {"Authorization": f"Bearer {designer_user['access_token']}"}

    resp = await client.post(f"/designer/start_task/{task_id}", headers=headers_designer)
    resp.raise_for_status()

    return resp.json()
