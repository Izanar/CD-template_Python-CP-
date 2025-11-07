import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestCreateWebMasterTeam:
    async def test_create_team_success(self, admin_user, client):
        resp = await client.post(
            "/admin/web_master_team/create",
            json={"team_name": "AlphaTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert isinstance(data["id"], int)
        assert data["name"] == "AlphaTeam"
        assert data.get("lead_id") is None

    async def test_create_duplicate_team(self, admin_user, client):
        team_name = "DuplicateTeam"
        resp1 = await client.post(
            "/admin/web_master_team/create",
            json={"team_name": team_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code in (200, 201), resp1.text

        resp2 = await client.post(
            "/admin/web_master_team/create",
            json={"team_name": team_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 409
        assert "team with this name already exists" in resp2.text.lower()

    async def test_create_team_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/web_master_team/create",
                json={"team_name": "ForbiddenTeam"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_create_team_missing_name(self, admin_user, client):
        resp = await client.post(
            "/admin/web_master_team/create",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
