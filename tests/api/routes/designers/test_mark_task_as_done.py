import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [
    UserRole.media_buyer,
    UserRole.lead_media_buyer,
    UserRole.designer,
    UserRole.lead_designer,
    UserRole.admin,
]


@pytest.mark.asyncio
class TestMarkTaskAsDone:
    endpoint = "/designer/mark_task_as_done/{task_id}"

    async def test_mark_done_success(self, client: AsyncClient, admin_user, designer_file):
        task_id, _file_id, _headers = designer_file
        hdr = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp = await client.post(self.endpoint.format(task_id=task_id), headers=hdr)
        assert resp.status_code == 200
        assert resp.json()["task_status"] == "under_tl_review"

    async def test_mark_done_without_media_files_fails(self, client: AsyncClient, admin_user, task_in_progress):
        task_id = task_in_progress["id"]
        hdr = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp = await client.post(self.endpoint.format(task_id=task_id), headers=hdr)
        assert resp.status_code == 409
        assert "media file" in resp.json()["detail"].lower()

    async def test_task_not_found_returns_404(self, client: AsyncClient, admin_user):
        hdr = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.post(self.endpoint.format(task_id=999_999), headers=hdr)
        assert resp.status_code == 404

    async def test_access_restricted_for_other_roles(self, client: AsyncClient, restricted_users):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            hdr = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.post(self.endpoint.format(task_id=1), headers=hdr)
            assert resp.status_code in (400, 401, 403, 409)

    async def test_operational_task_goes_to_completed_not_buyer_review(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_tasks_with_operational,
        designer_file,
    ):
        operational_tasks = await make_tasks_with_operational(
            status=DesignerTaskStatus.IN_PROGRESS,
            assigned_to_id=lead_designer_user["id"],
            count=1,
        )
        task_id = operational_tasks[0].id

        _, _file_id, _headers = designer_file

        hdr = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.post(self.endpoint.format(task_id=task_id), headers=hdr)

        assert resp.status_code == 200
        result = resp.json()
        assert result["task_status"] == DesignerTaskStatus.COMPLETED.value
