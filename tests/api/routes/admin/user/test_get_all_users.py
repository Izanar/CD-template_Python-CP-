from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestGetUsersEndpoint:
    async def test_get_users_default_pagination(self, admin_user, client: AsyncClient):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get("/admin/user/all", headers=headers)
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert "meta" in body and "items" in body
        meta = body["meta"]
        items = body["items"]

        assert meta["limit"] == 10
        assert meta["offset"] == 0
        assert isinstance(meta["total"], int)
        assert isinstance(items, list)

    async def test_get_users_with_limit_offset(self, admin_user, client: AsyncClient):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get("/admin/user/all?limit=1&offset=1", headers=headers)
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["meta"]["limit"] == 1
        assert body["meta"]["offset"] == 1
        assert len(body["items"]) <= 1

    async def test_get_users_filter_by_role(self, admin_user, client: AsyncClient, designer_user, media_buyer_user):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp1 = await client.get("/admin/user/all?role=designer", headers=headers)
        assert resp1.status_code == 200, resp1.text
        assert all(u["role"] == "designer" for u in resp1.json()["items"])

        resp2 = await client.get("/admin/user/all?role=media_buyer", headers=headers)
        assert resp2.status_code == 200, resp2.text
        assert all(u["role"] == "media_buyer" for u in resp2.json()["items"])

    async def test_get_users_ordering(self, admin_user, client: AsyncClient):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get("/admin/user/all?order_by=username&order_direction=asc", headers=headers)
        assert resp.status_code == 200, resp.text

        items = resp.json()["items"]
        usernames = [u["username"] for u in items]
        assert usernames == sorted(usernames)

    async def test_get_users_filter_created_at(self, admin_user, client: AsyncClient, make_user):
        today_utc = datetime.now(timezone.utc).date().isoformat()
        await make_user(UserRole.designer, username="today_user")
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get(f"/admin/user/all?created_at={today_utc}", headers=headers)
        assert resp.status_code == 200
        assert any(today_utc in u.get("created_at", "") for u in resp.json()["items"])

    async def test_get_users_unauthorized(self, client: AsyncClient):
        resp = await client.get("/admin/user/all")
        assert resp.status_code == 401

    async def test_get_all_users_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(
                "/admin/user/all",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "param, value",
        [
            ("limit", 0),
            ("limit", 1001),
            ("offset", -1),
            ("order_direction", "up"),
        ],
    )
    async def test_get_users_invalid_query_params(self, admin_user, client: AsyncClient, param, value):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get(f"/admin/user/all?{param}={value}", headers=headers)
        assert resp.status_code == 422

    async def test_get_users_invalid_order_by_field(self, admin_user, client: AsyncClient):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.get("/admin/user/all?order_by=foobar", headers=headers)
        assert resp.status_code in (400, 422)
