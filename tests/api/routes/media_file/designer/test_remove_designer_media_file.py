import uuid

import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ENDPOINT = "/media_files/designer/{task_id}"


@pytest.mark.asyncio
class TestRemoveDesignerMediaFile:
    async def test_success(self, client: AsyncClient, designer_file):
        task_id, file_id, headers = designer_file
        response = await client.delete(
            ENDPOINT.format(task_id=task_id),
            params={"file_id": file_id},
            headers=headers,
        )
        assert response.status_code == 200
        assert not response.json()["files"]

    async def test_file_not_found(self, client: AsyncClient, designer_file):
        task_id, _, headers = designer_file
        response = await client.delete(
            ENDPOINT.format(task_id=task_id),
            params={"file_id": uuid.uuid4().int >> 96},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_task_not_owned(self, client: AsyncClient, designer_file, make_user):
        designer_user = await make_user(UserRole.designer)
        task_id, file_id, _ = designer_file
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
        response = await client.delete(
            ENDPOINT.format(task_id=task_id),
            params={"file_id": file_id},
            headers=headers,
        )
        assert response.status_code == 403
