import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus


@pytest.mark.asyncio
async def test_update_celebrities_success(
    client: AsyncClient,
    media_buyer_user,
    lead_designer_user,
    new_task,
    celebrity_1,
    celebrity_2,
    celebrity_3,
):
    """Test that lead designer can update celebrities for a task"""
    lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}

    # First, update task with celebrities
    resp = await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": new_task["id"],
            "celebrities": [celebrity_1["id"], celebrity_2["id"]],
        },
        headers=lead_headers,
    )
    resp.raise_for_status()
    data = resp.json()

    assert "celebrities" in data
    assert len(data["celebrities"]) == 2
    assert {c["id"] for c in data["celebrities"]} == {celebrity_1["id"], celebrity_2["id"]}

    # Update with different celebrities
    resp2 = await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": new_task["id"],
            "celebrities": [celebrity_2["id"], celebrity_3["id"]],
        },
        headers=lead_headers,
    )
    resp2.raise_for_status()
    data2 = resp2.json()

    assert "celebrities" in data2
    assert len(data2["celebrities"]) == 2
    assert {c["id"] for c in data2["celebrities"]} == {celebrity_2["id"], celebrity_3["id"]}


@pytest.mark.asyncio
async def test_keep_designer_if_field_absent(
    client: AsyncClient,
    media_buyer_user,
    lead_designer_user,
    designer_user,
    new_task,
    new_difficulty,
):
    buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}

    diff_id = (await new_difficulty())["id"]
    await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": new_task["id"],
            "assigned_to_id": designer_user["id"],
            "difficulty_ids": [{"id": diff_id}],
        },
        headers=lead_headers,
    )

    resp = await client.patch(
        f"/media_buyer/designer/{new_task['id']}/update",
        json={"deadline": "2030-01-01T10:00:00Z"},
        headers=buyer_headers,
    )
    resp.raise_for_status()
    data = resp.json()

    assert data["assigned_to_user"]["id"] == designer_user["id"]
    assert data["task_status"] == DesignerTaskStatus.WAITING_TO_START.value


@pytest.mark.asyncio
async def test_unassign_designer_when_null(
    client: AsyncClient,
    lead_designer_user,
    designer_user,
    new_task,
    new_difficulty,
):
    lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}

    diff_id = (await new_difficulty())["id"]
    await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": new_task["id"],
            "assigned_to_id": designer_user["id"],
            "difficulty_ids": [{"id": diff_id}],
        },
        headers=lead_headers,
    )

    resp = await client.patch(
        "/lead_designer/task/update",
        json={"task_id": new_task["id"], "assigned_to_id": None},
        headers=lead_headers,
    )
    resp.raise_for_status()
    data = resp.json()

    assert data["assigned_to_user"] is None
    assert data["task_status"] == "waiting_to_assign"


@pytest.mark.asyncio
async def test_lead_designer_can_update_celebrities_any_status(
    client: AsyncClient,
    lead_designer_user,
    designer_user,
    new_task,
    celebrity_1,
    new_difficulty,
):
    """Test that lead designer can update celebrities regardless of task status"""
    lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}

    diff_id = (await new_difficulty())["id"]
    # Assign task to designer
    await client.patch(
        "/lead_designer/task/update",
        json={
            "task_id": new_task["id"],
            "assigned_to_id": designer_user["id"],
            "difficulty_ids": [{"id": diff_id}],
        },
        headers=lead_headers,
    )

    # Lead designer updates celebrities when task is WAITING_TO_START
    resp = await client.patch(
        "/lead_designer/task/update",
        json={"task_id": new_task["id"], "celebrities": [celebrity_1["id"]]},
        headers=lead_headers,
    )
    resp.raise_for_status()
    data = resp.json()

    assert "celebrities" in data
    assert len(data["celebrities"]) == 1
    assert data["celebrities"][0]["id"] == celebrity_1["id"]


@pytest.mark.asyncio
async def test_designer_cannot_update_celebrities_unless_in_progress(
    client: AsyncClient,
    designer_user,
    new_task,
    celebrity_1,
):
    """Test that designer cannot update celebrities when task is not IN_PROGRESS"""
    designer_headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

    # Try to update celebrities on task in DRAFT status (should fail)
    resp = await client.patch(
        "/lead_designer/task/update",
        json={"task_id": new_task["id"], "celebrities": [celebrity_1["id"]]},
        headers=designer_headers,
    )
    assert resp.status_code == 409
    assert "IN_PROGRESS" in resp.json()["detail"]
