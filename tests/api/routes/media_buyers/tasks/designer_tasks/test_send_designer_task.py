import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer]


@pytest.mark.asyncio
class TestSendDesignerTask:
    endpoint = "/media_buyer/designer/{task_id}/send"

    async def test_send_draft_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_draft_task,
    ):
        draft = new_draft_task
        assert draft["task_status"].lower() == "draft"

        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=draft["id"]),
            headers=headers,
        )
        assert resp.status_code == 200
        sent = resp.json()
        assert sent["id"] == draft["id"]
        assert sent["task_status"].lower() == "waiting_to_assign"

    async def test_send_non_draft_fails(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_task,
    ):
        task = new_task
        assert task["task_status"].lower() != "draft"

        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=task["id"]),
            headers=headers,
        )
        assert resp.status_code == 409
        assert f"Task with ID {task['id']} must be in DRAFT status to be sent." in resp.json()["detail"]

    async def test_send_nonexistent_task_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(self.endpoint.format(task_id=999_999), headers=headers)
        assert resp.status_code == 404

    async def test_send_not_owner_returns_403(
        self,
        client: AsyncClient,
        new_draft_task,
        make_user,
    ):
        task_id = new_draft_task["id"]
        other = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other['access_token']}"}
        resp = await client.patch(self.endpoint.format(task_id=task_id), headers=headers)
        assert resp.status_code == 403

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.patch(self.endpoint.format(task_id=1), headers=headers)
            assert resp.status_code in (401, 403)
