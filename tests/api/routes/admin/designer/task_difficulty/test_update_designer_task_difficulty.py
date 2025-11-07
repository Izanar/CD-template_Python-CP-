import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUpdateTaskDifficulty:
    async def test_update_difficulty_success(self, new_difficulty, admin_user, client):
        created = await new_difficulty(name="orig_easy", points=5)
        difficulty_id = created["id"]

        update_resp = await client.patch(
            f"/admin/designer/tasks/update_difficulty?difficulty_id={difficulty_id}",
            json={"name": "updated_easy", "points": 8},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert update_resp.status_code == 200, update_resp.text
        updated = update_resp.json()
        assert updated["id"] == difficulty_id
        assert updated["name"] == "updated_easy"
        assert updated["points"] == 8

    async def test_update_partial_points_only(self, new_difficulty, admin_user, client):
        created = await new_difficulty(name="orig_mid", points=10)
        difficulty_id = created["id"]

        resp = await client.patch(
            f"/admin/designer/tasks/update_difficulty?difficulty_id={difficulty_id}",
            json={"points": 15},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text
        result = resp.json()
        assert result["id"] == difficulty_id
        assert result["name"] == "orig_mid"
        assert result["points"] == 15

    async def test_update_conflict_name(self, new_difficulty, admin_user, client):
        await new_difficulty(name="conflict_one", points=1)
        second = await new_difficulty(name="conflict_two", points=2)
        second_id = second["id"]

        conflict_resp = await client.patch(
            f"/admin/designer/tasks/update_difficulty?difficulty_id={second_id}",
            json={"name": "conflict_one"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert conflict_resp.status_code == 409

    async def test_update_not_found(self, admin_user, client):
        resp = await client.patch(
            "/admin/designer/tasks/update_difficulty?difficulty_id=999999",
            json={"name": "no_such"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_update_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.patch(
                "/admin/designer/tasks/update_difficulty?difficulty_id=1",
                json={"points": 1},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("bad_name", [123, True])
    async def test_update_invalid_name_type(self, new_difficulty, admin_user, client, bad_name):
        created = await new_difficulty(points=4)
        test_id = created["id"]

        resp = await client.patch(
            f"/admin/designer/tasks/update_difficulty?difficulty_id={test_id}",
            json={"name": bad_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
