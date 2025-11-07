import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestDeleteTaskDifficulty:
    async def test_delete_difficulty_success(self, new_difficulty, admin_user, client):
        created = await new_difficulty(name="to_delete", points=7)
        difficulty_id = created["id"]

        delete_resp = await client.delete(
            f"/admin/designer/tasks/remove_difficulty?difficulty_id={difficulty_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert delete_resp.status_code == 200, delete_resp.text

    async def test_delete_not_found(self, admin_user, client):
        resp = await client.delete(
            "/admin/designer/tasks/remove_difficulty?difficulty_id=999999",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_delete_forbidden_for_non_admin(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                "/admin/designer/tasks/remove_difficulty?difficulty_id=1",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("bad_id", ["abc", 1.2])
    async def test_delete_invalid_id_type(self, admin_user, client, bad_id):
        resp = await client.delete(
            f"/admin/designer/tasks/remove_difficulty?difficulty_id={bad_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
