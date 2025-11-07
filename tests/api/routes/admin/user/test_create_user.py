import pytest

from app.schemas.enums.user import UserRole
from tests.fixtures.users import TEST_ROLES

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUserCreation:
    @pytest.mark.parametrize("role", TEST_ROLES)
    async def test_create_and_get_profile(self, make_user, role):
        user = await make_user(role)

        assert "id" in user
        assert user["username"] is not None
        assert user["role"] == role.value
        assert "created_at" in user
        assert "access_token" in user

    async def test_create_user_forbidden_for_non_admin(self, restricted_users, client):
        for role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/user/create",
                json={
                    "role": role,
                    "username": "should_not_create",
                    "password": "password123",
                },
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("invalid_role", ["not_a_real_role"])
    async def test_create_user_invalid_role(self, admin_user, client, invalid_role):
        resp = await client.post(
            "/admin/user/create",
            json={
                "role": invalid_role,
                "username": "badrole",
                "password": "password123",
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (400, 422)

    async def test_create_user_missing_fields(self, admin_user, client):
        resp = await client.post(
            "/admin/user/create",
            json={},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
