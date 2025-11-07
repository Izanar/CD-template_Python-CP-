import uuid

import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestCreateWebMasterTaskType:
    async def test_create_task_type_as_admin(self, admin_user, client: AsyncClient):
        unique_name = f"test_web_master_task_type_{uuid.uuid4().hex}"
        payload = {"name": unique_name}
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp = await client.post(
            "/admin/web_master/tasks/create_type",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == unique_name
        assert "id" in data

    async def test_create_task_type_duplicate_name(self, admin_user, client: AsyncClient):
        unique_name = f"test_web_master_task_type_{uuid.uuid4().hex}"
        payload = {"name": unique_name}
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp1 = await client.post(
            "/admin/web_master/tasks/create_type",
            json=payload,
            headers=headers,
        )
        assert resp1.status_code in (200, 201)

        resp2 = await client.post(
            "/admin/web_master/tasks/create_type",
            json=payload,
            headers=headers,
        )
        assert resp2.status_code == 409
        detail = resp2.json()["detail"]
        assert unique_name in detail
        assert "already exists" in detail

    async def test_create_task_type_access_restricted(self, restricted_users, client: AsyncClient):
        for role, user in restricted_users(*ALLOWED_ROLES):
            forbidden_name = f"forbidden_{role.name}_{uuid.uuid4().hex}"
            payload = {"name": forbidden_name}
            headers = {"Authorization": f"Bearer {user['access_token']}"}

            resp = await client.post(
                "/admin/web_master/tasks/create_type",
                json=payload,
                headers=headers,
            )
            assert resp.status_code in (401, 403)
