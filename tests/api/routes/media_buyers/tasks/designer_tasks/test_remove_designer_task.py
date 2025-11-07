import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer, UserRole.admin, UserRole.lead_designer]

ENDPOINT = "/media_buyer/designer/{task_id}/remove"


@pytest.mark.asyncio
class TestRemoveDesignerTask:
    async def test_remove_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_draft_task,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        response = await client.delete(ENDPOINT.format(task_id=new_draft_task["id"]), headers=headers)
        assert response.status_code == 200
        assert response.json()["task_id"] == new_draft_task["id"]

        second_try = await client.delete(ENDPOINT.format(task_id=new_draft_task["id"]), headers=headers)
        assert second_try.status_code == 404

    async def test_remove_nonexistent_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        response = await client.delete(ENDPOINT.format(task_id=999_999), headers=headers)
        assert response.status_code == 404

    async def test_remove_not_owner_returns_404(
        self,
        client: AsyncClient,
        make_user,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
    ):
        other_buyer = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {other_buyer['access_token']}"}
        response = await client.delete(ENDPOINT.format(task_id=new_task["id"]), headers=headers)
        assert response.status_code == 403

    async def test_access_restricted_roles(
        self,
        client: AsyncClient,
        restricted_users,
        new_task,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            response = await client.delete(ENDPOINT.format(task_id=new_task["id"]), headers=headers)
            assert response.status_code in (401, 403)
