import pytest
from httpx import AsyncClient

from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer]


@pytest.mark.asyncio
class TestSaveAndSendDesignerTask:
    endpoint = "/media_buyer/designer/{task_id}/save-send"

    async def test_save_and_send_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_draft_task,
    ):
        assert new_draft_task["task_status"].lower() == "draft"
        task_id = new_draft_task["id"]

        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json={"description": "updated and sent"},
            headers=headers,
        )
        assert resp.status_code == 200

        result = resp.json()
        assert result["id"] == task_id
        assert result["description"] == "updated and sent"
        assert result["task_status"].lower() == "waiting_to_assign"

    async def test_save_and_send_non_draft_fails(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_task,
    ):
        assert new_task["task_status"].lower() != "draft"
        task_id = new_task["id"]

        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json={"description": "won't work"},
            headers=headers,
        )
        assert resp.status_code == 409
        assert f"Task with ID {task_id} must be in DRAFT status to be saved and sent." in resp.json()["detail"]

    async def test_save_and_send_nonexistent_task_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=999_999),
            json={"description": "x", "task_type": DesignerTaskTypeEnum.land_video.value},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_save_and_send_not_owner_returns_404(
        self,
        client: AsyncClient,
        new_draft_task,
        make_user,
    ):
        task_id = new_draft_task["id"]
        other = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other['access_token']}"}

        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json={"description": "malicious", "task_type": DesignerTaskTypeEnum.land_video.value},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        new_draft_task,
        restricted_users,
    ):
        task_id = new_draft_task["id"]

        for _role, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.patch(
                self.endpoint.format(task_id=task_id),
                json={"description": "attempted access"},
                headers=headers,
            )
            assert resp.status_code in (401, 403), f"{_role} got {resp.status_code}: {resp.text}"
