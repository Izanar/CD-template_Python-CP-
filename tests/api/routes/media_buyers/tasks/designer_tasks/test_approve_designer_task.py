import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin, UserRole.media_buyer, UserRole.lead_media_buyer]


@pytest.mark.asyncio
class TestApproveDesignerTask:
    endpoint = "/media_buyer/designer/{task_id}/approve"

    async def test_approve_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task_under_review,
    ):
        task_id = new_task_under_review["id"]
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.post(self.endpoint.format(task_id=task_id), json={}, headers=headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["id"] == task_id
        assert data["task_status"].lower() == DesignerTaskStatus.COMPLETED.value.lower()

    async def test_approve_nonexistent_task_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.post(self.endpoint.format(task_id=999_999), json={}, headers=headers)
        assert resp.status_code == 404

    async def test_approve_not_owner_returns_404(
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

        resp = await client.post(self.endpoint.format(task_id=task_id), json={}, headers=headers)
        assert resp.status_code == 403

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.post(self.endpoint.format(task_id=1), json={}, headers=headers)
            assert resp.status_code in (401, 403)
