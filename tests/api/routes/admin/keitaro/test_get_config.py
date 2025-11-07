import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestGetKeitaroConfig:
    async def test_get_config_success(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.get(
            f"/admin/keitaro/config/{config_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == config_id
        assert data["name"] == keitaro_config["name"]

    async def test_get_config_not_found(self, admin_user, client: AsyncClient):
        resp = await client.get(
            "/admin/keitaro/config/99999",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404
        data = resp.json()
        assert "not found" in data["detail"].lower()

    async def test_get_config_invalid_id_format(self, admin_user, client: AsyncClient):
        resp = await client.get(
            "/admin/keitaro/config/invalid_id",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 422

    async def test_get_config_forbidden_for_non_admin(self, restricted_users, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        for _, user in restricted_users(UserRole.admin):
            resp = await client.get(
                f"/admin/keitaro/config/{config_id}",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_get_config_unauthorized(self, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.get(f"/admin/keitaro/config/{config_id}")
        assert resp.status_code == 401
