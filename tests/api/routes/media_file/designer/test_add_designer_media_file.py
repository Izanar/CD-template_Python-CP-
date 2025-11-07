from pathlib import Path

import pytest
from httpx import AsyncClient

ENDPOINT = "/media_files/designer/{task_id}"


@pytest.mark.asyncio
class TestAddDesignerMediaFile:
    async def test_success(self, client: AsyncClient, media_buyer_user, task_in_progress, sample_image):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        with Path.open(sample_image, "rb") as image:
            response = await client.post(
                ENDPOINT.format(task_id=task_in_progress["id"]),
                files={"media_file": ("image.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 200
        assert response.json()["id"] == task_in_progress["id"]

    async def test_task_not_owned(self, client: AsyncClient, designer_user, new_task, sample_image):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
        with Path.open(sample_image, "rb") as image:
            response = await client.post(
                ENDPOINT.format(task_id=new_task["id"]),
                files={"media_file": ("image.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 403

    async def test_task_absent(self, client: AsyncClient, media_buyer_user, sample_image):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        with Path.open(sample_image, "rb") as image:
            response = await client.post(
                ENDPOINT.format(task_id=999_999),
                files={"media_file": ("image.jpg", image, "image/jpeg")},
                headers=headers,
            )
        assert response.status_code == 404
