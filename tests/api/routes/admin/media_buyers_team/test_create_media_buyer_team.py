import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestCreateMediaBuyerTeam:
    async def test_create_team_success(self, admin_user, client):
        resp = await client.post(
            "/admin/media_buyers_team/create",
            json={"name": "AlphaTeam", "prefix": "Prefix"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data["id"], int)
        assert data["name"] == "AlphaTeam"
        assert data.get("lead_id") is None
        assert data.get("responsible_designer_id") is None
        assert data.get("responsible_web_master_id") is None
        assert data.get("has_keitaro_config") is False

    async def test_create_duplicate_team_or_prefix(self, admin_user, client):
        team_name = "DuplicateTeam"
        prefix = "random_prefix"
        resp1 = await client.post(
            "/admin/media_buyers_team/create",
            json={"name": team_name, "prefix": prefix},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code == 200, resp1.text

        resp2 = await client.post(
            "/admin/media_buyers_team/create",
            json={"name": team_name, "prefix": prefix},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 409
        assert "team with this name already exists" in resp2.text.lower()

        resp3 = await client.post(
            "/admin/media_buyers_team/create",
            json={"name": "Random_name", "prefix": prefix},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp3.status_code == 409
        assert "team with this prefix already exists" in resp3.text.lower()

    async def test_create_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/media_buyers_team/create",
                json={"name": "X", "prefix": "random_prefix"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_create_missing_name(self, admin_user, client):
        resp = await client.post(
            "/admin/media_buyers_team/create",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
