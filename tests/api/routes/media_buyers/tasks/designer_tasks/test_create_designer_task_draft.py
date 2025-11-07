import pytest
from httpx import AsyncClient

from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer]


@pytest.mark.asyncio
class TestCreateDesignerTaskDraft:
    endpoint = "/media_buyer/designer/create_draft"

    async def test_create_draft_as_media_buyer(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
    ):
        payload = {"description": "Draft-path task", "task_type": DesignerTaskTypeEnum.land_video.value}
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)

        data = resp.json()
        assert data["description"] == payload["description"]
        assert data["task_type"] == DesignerTaskTypeEnum.land_video.value
        assert data["task_status"] == "draft"

    async def test_create_draft_with_invalid_task_type(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        payload = {"description": "Bad draft type", "task_type": "invalid_type"}
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code == 422  # Validation error for invalid enum value

    async def test_create_draft_without_team(
        self,
        client: AsyncClient,
        make_user,
    ):
        fresh_buyer = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {fresh_buyer['access_token']}"}
        payload = {"description": "No-team draft", "task_type": DesignerTaskTypeEnum.land_video.value}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code == 404
        assert "Team ID not found" in resp.json()["detail"]

    async def test_draft_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for role, user in restricted_users(*ALLOWED_ROLES):
            payload = {
                "description": f"Denied draft for {role}",
                "task_type": DesignerTaskTypeEnum.land_video.value,
            }
            headers = {"Authorization": f"Bearer {user['access_token']}"}

            resp = await client.post(self.endpoint, json=payload, headers=headers)
            assert resp.status_code in (401, 403, 404)
