from pathlib import Path

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def designer_file(client: AsyncClient, designer_user, task_in_progress, sample_image):
    headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
    with Path.open(sample_image, "rb") as image:
        response = await client.post(
            f"/media_files/designer/{task_in_progress['id']}",
            files={"media_file": ("sample.jpg", image, "image/jpeg")},
            headers=headers,
        )
    response.raise_for_status()
    file_id = response.json()["files"][0]["id"]
    yield task_in_progress["id"], file_id, headers
    await client.delete(
        f"/media_files/designer/{task_in_progress['id']}",
        params={"file_id": file_id},
        headers=headers,
    )
