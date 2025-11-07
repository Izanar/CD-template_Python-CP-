import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestDeleteKeitaroConfig:
    async def test_delete_config_success(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.get(
            f"/admin/keitaro/config/{config_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200

        resp = await client.delete(
            f"/admin/keitaro/config/{config_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 204
        assert resp.content == b""

        resp = await client.get(
            f"/admin/keitaro/config/{config_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_delete_config_not_found(self, admin_user, client: AsyncClient):
        resp = await client.delete(
            "/admin/keitaro/config/99999",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404

    async def test_delete_config_invalid_id_format(self, admin_user, client: AsyncClient):
        resp = await client.delete(
            "/admin/keitaro/config/invalid_id",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 422

    async def test_delete_config_forbidden_for_non_admin(self, restricted_users, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        for _, user in restricted_users(UserRole.admin):
            resp = await client.delete(
                f"/admin/keitaro/config/{config_id}",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_delete_config_unauthorized(self, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.delete(f"/admin/keitaro/config/{config_id}")
        assert resp.status_code == 401

    async def test_delete_config_verify_list_after_deletion(self, admin_user, client: AsyncClient, keitaro_config):
        config_id = keitaro_config["id"]

        resp = await client.get(
            "/admin/keitaro/config",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200
        configs_before = resp.json()
        config_ids_before = [config["id"] for config in configs_before]
        assert config_id in config_ids_before

        resp = await client.delete(
            f"/admin/keitaro/config/{config_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 204

        resp = await client.get(
            "/admin/keitaro/config",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200
        configs_after = resp.json()
        config_ids_after = [config["id"] for config in configs_after]
        assert config_id not in config_ids_after
        assert len(configs_after) == len(configs_before) - 1
