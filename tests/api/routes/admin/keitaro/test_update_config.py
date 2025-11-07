import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestUpdateKeitaroConfig:
    async def test_update_config_single_field(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.patch(
            f"/admin/keitaro/config/{config_id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == config_id
        assert data["name"] == "Updated Name"

    async def test_update_config_multiple_fields(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.patch(
            f"/admin/keitaro/config/{config_id}",
            json={
                "name": "Updated Name",
                "api_key": "updated_api_key",
                "base_url": "https://updated.com",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["base_url"] == "https://updated.com"

    async def test_update_config_empty_json(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]
        original_data = keitaro_config.copy()

        resp = await client.patch(
            f"/admin/keitaro/config/{config_id}",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == original_data["name"]

    async def test_update_config_not_found(self, admin_user, client: AsyncClient):
        resp = await client.patch(
            "/admin/keitaro/config/99999",
            json={"name": "Should Not Update"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404

    async def test_update_config_invalid_data_types(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.patch(
            f"/admin/keitaro/config/{config_id}",
            json={
                "name": 123,
                "api_key": True,
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 422

    async def test_update_config_forbidden_for_non_admin(self, restricted_users, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        for _, user in restricted_users(UserRole.admin):
            resp = await client.patch(
                f"/admin/keitaro/config/{config_id}",
                json={"name": "Should Not Update"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_update_config_unauthorized(self, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.patch(
            f"/admin/keitaro/config/{config_id}",
            json={"name": "Unauthorized Update"},
        )
        assert resp.status_code == 401
