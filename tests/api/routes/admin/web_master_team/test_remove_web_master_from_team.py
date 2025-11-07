import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestRemoveWebMasterFromTeam:
    async def test_remove_web_master_success(
        self,
        admin_user,
        client,
        web_master_team_with_member,
    ):
        team_id, member_id = web_master_team_with_member

        resp = await client.delete(
            f"/admin/web_master_team/{team_id}/remove_web_master",
            params={"web_master_id": member_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

    async def test_remove_web_master_not_in_team(
        self,
        admin_user,
        client,
        web_master_team_with_lead,
        web_master_user,
    ):
        team_id, _ = web_master_team_with_lead

        resp = await client.delete(
            f"/admin/web_master_team/{team_id}/remove_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404
        assert "not in team" in resp.text.lower()

    async def test_remove_from_nonexistent_team(self, admin_user, client, web_master_user):
        resp = await client.delete(
            "/admin/web_master_team/999999/remove_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_forbidden_for_non_admin(
        self,
        restricted_users,
        client,
        web_master_team_with_member,
        web_master_user,
    ):
        team_id, _ = web_master_team_with_member
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/web_master_team/{team_id}/remove_web_master",
                params={"web_master_id": web_master_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
