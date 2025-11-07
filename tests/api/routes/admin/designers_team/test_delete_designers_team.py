import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestDeleteDesignersTeam:
    async def test_delete_team_success(self, admin_user, client, new_team):
        team_id = new_team
        del_resp = await client.delete(
            f"/admin/designers_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert del_resp.status_code == 200, del_resp.text
        assert del_resp.json() == {"message": f"Team with id {team_id} was deleted successfully"}

        del_resp2 = await client.delete(
            f"/admin/designers_team/{team_id}/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert del_resp2.status_code == 404, del_resp2.text

    async def test_delete_nonexistent_team(self, admin_user, client):
        resp = await client.delete(
            "/admin/designers_team/999999/remove",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404, resp.text
        assert resp.json() == {"detail": "Team with id 999999 not found"}

    async def test_delete_forbidden_for_non_admin(self, restricted_users, client, new_team):
        team_id = new_team
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/designers_team/{team_id}/remove",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403), (
                f"Expected 401/403 for role {_role}, got {resp.status_code}: {resp.text}"
            )
