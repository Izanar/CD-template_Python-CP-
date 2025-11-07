import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestListKeitaroConfigs:
    async def test_list_configs_empty(self, admin_user, client: AsyncClient):
        resp = await client.get(
            "/admin/keitaro/config",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_list_configs_with_data(self, admin_user, client: AsyncClient, multiple_keitaro_configs):
        resp = await client.get(
            "/admin/keitaro/config",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least 2 configs from fixture

        for config in data:
            assert "id" in config
            assert "name" in config
            assert "base_url" in config
            assert "creo" in config
            assert "created_at" in config
            assert "is_active" in config
            assert "api_key" not in config

    async def test_list_configs_forbidden_for_non_admin(self, restricted_users, client: AsyncClient):
        for _, user in restricted_users(UserRole.admin):
            resp = await client.get(
                "/admin/keitaro/config",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_list_configs_unauthorized(self, client: AsyncClient):
        resp = await client.get("/admin/keitaro/config")
        assert resp.status_code == 401
