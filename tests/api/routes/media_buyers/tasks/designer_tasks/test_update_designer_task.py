import pytest
from httpx import AsyncClient

from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer]


@pytest.mark.asyncio
class TestUpdateDesignerTask:
    endpoint = "/media_buyer/designer/{task_id}/update"

    async def test_update_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_draft_task,
        celebrity_1,
        celebrity_3,
    ):
        task = new_draft_task
        task_id = task["id"]

        new_description = "updated description"
        payload = {
            "description": new_description,
            "task_type": DesignerTaskTypeEnum.land_video.value,
            "celebrities": [celebrity_1["id"], celebrity_3["id"]],
        }
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200

        updated = resp.json()
        assert updated["id"] == task_id
        assert updated["description"] == new_description
        assert "celebrities" in updated
        assert len(updated["celebrities"]) == 2
        assert {c["id"] for c in updated["celebrities"]} == {celebrity_1["id"], celebrity_3["id"]}

    async def test_update_invalid_task_type_fails(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_draft_task,
    ):
        task_id = new_draft_task["id"]
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        payload = {
            "description": "doesn't matter",
            "task_type": "invalid_type",
        }
        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 422  # Validation error for invalid enum value

    async def test_update_nonexistent_task_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        payload = {"description": "x", "task_type": DesignerTaskTypeEnum.land_video.value}
        resp = await client.patch(
            self.endpoint.format(task_id=999_999),
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Task with ID 999999 not found"

    async def test_update_not_owner_returns_403(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_draft_task,
        make_user,
    ):
        task_id = new_draft_task["id"]
        other = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other['access_token']}"}
        payload = {
            "description": "malicious update",
            "task_type": DesignerTaskTypeEnum.land_video.value,
        }
        resp = await client.patch(
            self.endpoint.format(task_id=task_id),
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "You did not create this task"

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.patch(
                self.endpoint.format(task_id=1),
                json={"description": "x", "task_type": DesignerTaskTypeEnum.land_video.value},
                headers=headers,
            )
            assert resp.status_code in (401, 403)
