import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestCreateKeitaroConfig:
    async def test_create_config_success(self, admin_user, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config",
            json={
                "name": "Test Keitaro Config",
                "api_key": "test_api_key_123",
                "base_url": "https://test.keitaro.com",
                "creo": "test_creo_123",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Test Keitaro Config"
        assert data["is_active"] is True

    async def test_create_config_duplicate_name(self, admin_user, client: AsyncClient, keitaro_config):
        resp = await client.post(
            "/admin/keitaro/config",
            json={
                "name": keitaro_config["name"],
                "api_key": "different_key",
                "base_url": "https://different.com",
                "creo": "different_creo",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 201

    async def test_create_config_missing_fields(self, admin_user, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config",
            json={"name": "Incomplete Config"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422

    async def test_create_config_invalid_data_types(self, admin_user, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config",
            json={
                "name": 123,
                "api_key": "valid_key",
                "base_url": "https://valid.com",
                "creo": "valid_creo",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422

    async def test_create_config_forbidden_for_non_admin(self, restricted_users, client: AsyncClient):
        for _, user in restricted_users(UserRole.admin):
            resp = await client.post(
                "/admin/keitaro/config",
                json={
                    "name": "Should Not Create",
                    "api_key": "forbidden_key",
                    "base_url": "https://forbidden.com",
                    "creo": "forbidden_creo",
                },
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_create_config_unauthorized(self, client: AsyncClient):
        resp = await client.post(
            "/admin/keitaro/config",
            json={
                "name": "Unauthorized Config",
                "api_key": "unauthorized_key",
                "base_url": "https://unauthorized.com",
                "creo": "unauthorized_creo",
            },
        )
        assert resp.status_code == 401
