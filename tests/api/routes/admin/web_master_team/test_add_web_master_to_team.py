import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddWebMasterToTeam:
    async def test_add_web_master_success(
        self,
        admin_user,
        client,
        web_master_team_with_lead,
        web_master_user,
    ):
        team_id, _ = web_master_team_with_lead

        resp = await client.post(
            f"/admin/web_master_team/{team_id}/add_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["id"] == team_id
        assert any(m["id"] == web_master_user["id"] for m in data["members"])

    async def test_add_web_master_no_lead(
        self,
        admin_user,
        client,
        web_master_team,
        web_master_user,
    ):
        team_id, _ = web_master_team

        resp = await client.post(
            f"/admin/web_master_team/{team_id}/add_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 403
        assert "no lead" in resp.text.lower()

    async def test_add_to_nonexistent_team(self, admin_user, client, web_master_user):
        resp = await client.post(
            "/admin/web_master_team/999999/add_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_nonexistent_web_master(
        self,
        admin_user,
        client,
        web_master_team_with_lead,
    ):
        team_id, _ = web_master_team_with_lead

        resp = await client.post(
            f"/admin/web_master_team/{team_id}/add_web_master",
            params={"web_master_id": 999999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_web_master_duplicate(
        self,
        admin_user,
        client,
        web_master_team_with_lead,
        web_master_user,
    ):
        team_id, _ = web_master_team_with_lead

        await client.post(
            f"/admin/web_master_team/{team_id}/add_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp2 = await client.post(
            f"/admin/web_master_team/{team_id}/add_web_master",
            params={"web_master_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 409
        assert "already in team" in resp2.text.lower()

    async def test_add_forbidden_for_non_admin(
        self,
        restricted_users,
        client,
        web_master_team,
        web_master_user,
    ):
        team_id, _ = web_master_team
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                f"/admin/web_master_team/{team_id}/add_web_master",
                params={"web_master_id": web_master_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
