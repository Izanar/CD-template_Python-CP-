import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUpdateMediaBuyerTeam:
    async def test_update_name_only(self, admin_user, client, media_buyer_team):
        team_id, old_name, _ = await media_buyer_team()

        resp = await client.patch(
            f"/admin/media_buyers_team/{team_id}/update",
            json={"name": f"{old_name}_upd"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["id"] == team_id
        assert body["name"] == f"{old_name}_upd"

    async def test_update_nonexistent(self, admin_user, client):
        resp = await client.patch(
            "/admin/media_buyers_team/999999/update",
            json={"name": "NoTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_update_missing_body(self, admin_user, client, media_buyer_team):
        team_id, _, _ = await media_buyer_team()

        resp = await client.patch(
            f"/admin/media_buyers_team/{team_id}/update",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422

    async def test_update_forbidden_for_non_admin(self, restricted_users, client, media_buyer_team):
        team_id, _, _ = await media_buyer_team()

        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.patch(
                f"/admin/media_buyers_team/{team_id}/update",
                json={"name": "X"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
