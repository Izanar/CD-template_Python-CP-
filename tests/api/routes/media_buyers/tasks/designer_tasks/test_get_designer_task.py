import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [
    UserRole.media_buyer,
    UserRole.lead_media_buyer,
    UserRole.designer,
    UserRole.lead_designer,
    UserRole.admin,
]


@pytest.mark.asyncio
class TestGetDesignerTask:
    endpoint = "/media_buyer/designer/{task_id}"

    async def test_get_task_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
    ):
        task_id = new_task["id"]
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.get(self.endpoint.format(task_id=task_id), headers=headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["id"] == task_id
        assert data["description"] == new_task["description"]
        assert data["task_status"].lower() == new_task["task_status"].lower()
        assert data["task_type"] == new_task["task_type"]

    async def test_get_task_not_found(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.get(self.endpoint.format(task_id=999_999), headers=headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Task with ID 999999 not found"

    async def test_get_task_not_owner_returns_403(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
        make_user,
    ):
        task_id = new_task["id"]
        other = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other['access_token']}"}
        resp = await client.get(self.endpoint.format(task_id=task_id), headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "You did not create this task"

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.get(self.endpoint.format(task_id=1), headers=headers)
            assert resp.status_code in (401, 403)
