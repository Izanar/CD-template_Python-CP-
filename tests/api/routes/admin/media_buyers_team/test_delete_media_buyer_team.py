import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestDeleteMediaBuyerTeam:
    async def test_delete_team_success(self, admin_user, client, media_buyer_team):
        team_id, _, _ = await media_buyer_team()
        resp = await client.delete(
            f"/admin/media_buyers_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["message"] == f"Team with id {team_id} was deleted successfully"

    async def test_delete_nonexistent_team(self, admin_user, client):
        resp = await client.delete(
            "/admin/media_buyers_team/999999/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_delete_twice(self, admin_user, client, media_buyer_team):
        team_id, _, _ = await media_buyer_team()
        resp1 = await client.delete(
            f"/admin/media_buyers_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code == 200

        resp2 = await client.delete(
            f"/admin/media_buyers_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 404

    async def test_delete_forbidden_for_non_admin(self, restricted_users, client, media_buyer_team):
        team_id, _, _ = await media_buyer_team()

        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/media_buyers_team/{team_id}/remove",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
