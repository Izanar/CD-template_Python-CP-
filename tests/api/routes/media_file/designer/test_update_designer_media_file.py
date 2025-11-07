from pathlib import Path

import pytest
from httpx import AsyncClient

from app.schemas.enums.user import UserRole

ENDPOINT = "/media_files/designer/{task_id}"


@pytest.mark.asyncio
class TestUpdateDesignerMediaFile:
    async def test_success(self, client: AsyncClient, designer_file, sample_image):
        task_id, file_id, headers = designer_file
        with Path.open(sample_image, "rb") as image:
            response = await client.patch(
                ENDPOINT.format(task_id=task_id),
                params={"file_id": file_id},
                files={"media_file": ("updated.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 200

    async def test_file_not_found(self, client: AsyncClient, designer_file, sample_image):
        task_id, _, headers = designer_file
        with Path.open(sample_image, "rb") as image:
            response = await client.patch(
                ENDPOINT.format(task_id=task_id),
                params={"file_id": 999_999},
                files={"media_file": ("updated.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 404

    async def test_task_not_owned(self, client: AsyncClient, designer_file, make_user, sample_image):
        designer_user = await make_user(UserRole.designer)
        task_id, file_id, _ = designer_file
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
        with Path.open(sample_image, "rb") as image:
            response = await client.patch(
                ENDPOINT.format(task_id=task_id),
                params={"file_id": file_id},
                files={"media_file": ("updated.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 403
