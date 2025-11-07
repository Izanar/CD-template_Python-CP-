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
class TestStartTask:
    endpoint = "/designer/start_task/{task_id}"

    async def test_start_success(self, client: AsyncClient, admin_user, task_in_progress):
        task_id = task_in_progress["id"]
        hdr = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp = await client.post(self.endpoint.format(task_id=task_id), headers=hdr)
        assert resp.status_code == 200
        assert resp.json()["task_status"] == "in_progress"

    async def test_task_not_found_returns_404(self, client: AsyncClient, admin_user):
        hdr = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.post(self.endpoint.format(task_id=999_999), headers=hdr)
        assert resp.status_code == 404

    async def test_access_restricted_for_other_roles(self, client: AsyncClient, restricted_users):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            hdr = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.post(self.endpoint.format(task_id=1), headers=hdr)
            assert resp.status_code in (400, 401, 403, 409)
