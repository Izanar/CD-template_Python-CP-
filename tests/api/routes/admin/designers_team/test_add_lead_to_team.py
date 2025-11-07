import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddLeadToTeam:
    async def test_add_lead_success(self, admin_user, client, new_team, lead_designer_user):
        add_resp = await client.post(
            "/admin/designers_team/add_lead",
            json={"team_id": new_team, "lead_id": [lead_designer_user["id"]]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert add_resp.status_code == 200, add_resp.text
        data = add_resp.json()
        assert data["id"] == new_team
        assert any(lead["id"] == lead_designer_user["id"] for lead in data["lead_users"])

    async def test_add_lead_nonexistent_team(self, admin_user, client, lead_designer_user):
        resp = await client.post(
            "/admin/designers_team/add_lead",
            json={"team_id": 999999, "lead_id": [lead_designer_user["id"]]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (400, 404)
        assert "team" in resp.text.lower()

    async def test_add_nonexistent_lead(self, admin_user, client, new_team):
        resp = await client.post(
            "/admin/designers_team/add_lead",
            json={"team_id": new_team, "lead_id": [999999]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (400, 403, 404)

    async def test_add_lead_forbidden_for_non_admin(self, restricted_users, client, new_team, lead_designer_user):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/designers_team/add_lead",
                json={"team_id": new_team, "lead_id": [lead_designer_user["id"]]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_add_lead_missing_fields(self, admin_user, client):
        resp = await client.post(
            "/admin/designers_team/add_lead",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
