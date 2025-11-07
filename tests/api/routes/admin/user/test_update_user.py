import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUpdateUserEndpoint:
    async def test_update_user_success(self, admin_user, client: AsyncClient, make_user):
        original = await make_user(UserRole.designer, username="oldname", password="oldpass")  # noqa: S106
        user_id = original["id"]

        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        payload = {"username": "newname"}
        resp = await client.patch(f"/admin/user/{user_id}", json=payload, headers=headers)
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["id"] == user_id
        assert body["username"] == "newname"
        assert body["role"] == "designer"

    async def test_update_user_not_found(self, admin_user, client: AsyncClient):
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.patch("/admin/user/999999", json={"username": "doesntmatter"}, headers=headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User does not exist"

    async def test_update_user_unauthorized(self, client: AsyncClient):
        resp = await client.patch("/admin/user/1", json={"username": "x"})
        assert resp.status_code == 401

    async def test_update_user_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.patch(
                "/admin/user/1",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
