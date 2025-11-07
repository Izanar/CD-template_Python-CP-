import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestCreateTaskDifficulty:
    async def test_create_difficulty_success(self, new_difficulty):
        created = await new_difficulty(name="autotest_easy", points=5)
        assert isinstance(created.get("id"), int)
        assert created["name"] == "autotest_easy"
        assert created["points"] == 5

    async def test_create_difficulty_conflict(self, admin_user, client):
        name = "autotest_conflict"
        resp1 = await client.post(
            "/admin/designer/tasks/create_difficulty",
            json={"name": name, "points": 3},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code in (200, 201), resp1.text

        resp2 = await client.post(
            "/admin/designer/tasks/create_difficulty",
            json={"name": name, "points": 3},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 409

    async def test_create_difficulty_forbidden_for_non_admin(self, restricted_users, client):
        for role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/designer/tasks/create_difficulty",
                json={"name": f"noaccess_{role.value}", "points": 1},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_create_difficulty_missing_fields(self, admin_user, client):
        resp = await client.post(
            "/admin/designer/tasks/create_difficulty",
            json={"name": "missing_points"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("bad_points", ["a", 1.5])
    async def test_create_difficulty_invalid_points_type(self, admin_user, client, bad_points):
        resp = await client.post(
            "/admin/designer/tasks/create_difficulty",
            json={"name": f"bad_points_{bad_points}", "points": bad_points},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
