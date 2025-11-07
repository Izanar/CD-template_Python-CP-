import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestRemoveWebMasterTeam:
    async def test_remove_team_success(self, admin_user, client, web_master_team):
        team_id, _ = web_master_team
        del_resp = await client.delete(
            f"/admin/web_master_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert del_resp.status_code == 200

    async def test_remove_nonexistent_team(self, admin_user, client):
        resp = await client.delete(
            "/admin/web_master_team/999999/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_forbidden_for_non_admin(self, restricted_users, client, web_master_team):
        team_id, _ = web_master_team
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/web_master_team/{team_id}/remove",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
