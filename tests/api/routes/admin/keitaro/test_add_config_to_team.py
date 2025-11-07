import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestAddKeitaroConfigToTeam:
    async def test_add_config_to_team_success(self, admin_user, client: AsyncClient, keitaro_config, media_buyer_team):
        team_id, _, _ = await media_buyer_team()
        config_id = keitaro_config["id"]

        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={
                "team_id": team_id,
                "keitaro_config_id": config_id,
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "config" in data
        assert "team" in data
        assert data["config"]["id"] == config_id
        assert data["team"]["id"] == team_id

    async def test_add_config_to_team_invalid_team_id(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={
                "team_id": 99999,
                "keitaro_config_id": config_id,
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404

    async def test_add_config_to_team_invalid_config_id(self, admin_user, client: AsyncClient, media_buyer_team):
        team_id, _, _ = await media_buyer_team()

        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={
                "team_id": team_id,
                "keitaro_config_id": 99999,
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404

    async def test_add_config_to_team_missing_fields(self, admin_user, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 422

    async def test_add_config_to_team_invalid_data_types(self, admin_user, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={
                "team_id": "invalid_team_id",
                "keitaro_config_id": "invalid_config_id",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 422

    async def test_add_config_to_team_forbidden_for_non_admin(
        self, restricted_users, client: AsyncClient, keitaro_config, media_buyer_team
    ):
        team_id, _, _ = await media_buyer_team()
        config_id = keitaro_config["id"]

        for _, user in restricted_users(UserRole.admin):
            resp = await client.post(
                "/admin/keitaro/config/add_to_team",
                json={
                    "team_id": team_id,
                    "keitaro_config_id": config_id,
                },
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_add_config_to_team_unauthorized(self, client: AsyncClient, keitaro_config, media_buyer_team):
        team_id, _, _ = await media_buyer_team()
        config_id = keitaro_config["id"]

        resp = await client.post(
            "/admin/keitaro/config/add_to_team",
            json={
                "team_id": team_id,
                "keitaro_config_id": config_id,
            },
        )
        assert resp.status_code == 401
