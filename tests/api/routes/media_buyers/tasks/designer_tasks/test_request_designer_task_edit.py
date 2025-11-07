import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer, UserRole.admin]

ENDPOINT = "/media_buyer/designer/request_task_edit/{task_id}"


@pytest.mark.asyncio
class TestRequestDesignerTaskEdit:
    async def test_request_edit_success(
        self,
        client: AsyncClient,
        media_buyer_user: dict,
        new_task_under_review: dict,
    ):
        task_id = new_task_under_review["id"]
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        payload = {"description": "Please update the colors"}

        resp = await client.post(ENDPOINT.format(task_id=task_id), json=payload, headers=headers)
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.text}"

        data = resp.json()
        assert data["task_status"].lower() == DesignerTaskStatus.REQUESTED_CHANGES.value.lower()
        edits = data.get("edits", [])
        assert edits, "Expected at least one edit"
        assert any(e["description"] == payload["description"] for e in edits)

    async def test_request_edit_nonexistent_task_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user: dict,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        payload = {"description": "No such task"}

        resp = await client.post(ENDPOINT.format(task_id=999_999), json=payload, headers=headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_request_edit_not_owner_returns_403(
        self,
        client: AsyncClient,
        media_buyer_user: dict,
        new_task_under_review: dict,
        make_user,
    ):
        task_id = new_task_under_review["id"]
        other_buyer = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other_buyer['access_token']}"}
        payload = {"description": "Unauthorized edit"}

        resp = await client.post(ENDPOINT.format(task_id=task_id), json=payload, headers=headers)
        assert resp.status_code == 403
        assert "you did not create this task" in resp.json()["detail"].lower()

    async def test_request_edit_when_unsolved_exists_fails(
        self,
        client: AsyncClient,
        media_buyer_user: dict,
        new_task_under_review: dict,
    ):
        task_id = new_task_under_review["id"]
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        payload1 = {"description": "First edit request"}
        payload2 = {"description": "Second edit request"}

        r1 = await client.post(ENDPOINT.format(task_id=task_id), json=payload1, headers=headers)
        assert r1.status_code == 200

        r2 = await client.post(ENDPOINT.format(task_id=task_id), json=payload2, headers=headers)
        assert r2.status_code == 409
        assert "you can not change task with current task status -- requested_changes" in r2.json()["detail"].lower()

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
        new_task_under_review: dict,
    ):
        task_id = new_task_under_review["id"]
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.post(ENDPOINT.format(task_id=task_id), json={"description": "X"}, headers=headers)
            assert resp.status_code in (401, 403)
