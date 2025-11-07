import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddLeadWebMasterToTeam:
    async def test_add_lead_success(
        self,
        admin_user,
        client,
        web_master_team,
        lead_web_master_user,
    ):
        team_id, _ = web_master_team
        lead_id = lead_web_master_user["id"]

        resp = await client.post(
            "/admin/web_master_team/add_lead",
            json={"team_id": team_id, "lead_id": lead_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["id"] == team_id
        assert data["lead_id"] == lead_id

    async def test_add_lead_nonexistent_team(
        self,
        admin_user,
        client,
        web_master_user,
    ):
        resp = await client.post(
            "/admin/web_master_team/add_lead",
            json={"team_id": 999999, "lead_id": web_master_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404
        assert "team 999999 not found" in resp.text.lower()

    async def test_add_nonexistent_lead(
        self,
        admin_user,
        client,
        web_master_team,
    ):
        team_id, _ = web_master_team
        resp = await client.post(
            "/admin/web_master_team/add_lead",
            json={"team_id": team_id, "lead_id": 999999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_lead_forbidden_for_non_admin(
        self,
        restricted_users,
        client,
        web_master_team,
        web_master_user,
    ):
        team_id, _ = web_master_team
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/web_master_team/add_lead",
                json={"team_id": team_id, "lead_id": web_master_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_add_lead_missing_fields(self, admin_user, client):
        resp = await client.post(
            "/admin/web_master_team/add_lead",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
