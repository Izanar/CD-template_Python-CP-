import uuid

import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestDeleteWebMasterTaskType:
    async def test_delete_task_type_conflict_for_existing(self, admin_user, client: AsyncClient):
        unique_name = f"test_web_master_task_type_{uuid.uuid4().hex}"
        resp_create = await client.post(
            "/admin/web_master/tasks/create_type",
            json={"name": unique_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp_create.status_code in (200, 201)
        task_type_id = resp_create.json()["id"]

        resp_delete = await client.delete(
            f"/admin/web_master/tasks/remove_type/{task_type_id}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp_delete.status_code == 200

    async def test_delete_task_type_conflict_for_nonexistent(self, admin_user, client: AsyncClient):
        resp = await client.delete(
            "/admin/web_master/tasks/remove_type/999999",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Task type not found"

    async def test_delete_task_type_access_restricted(self, restricted_users, client: AsyncClient):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                "/admin/web_master/tasks/remove_type/1",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
