from pathlib import Path

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def web_master_file(client: AsyncClient, media_buyer_user, web_master_task_in_progress, sample_image):
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
    with Path.open(sample_image, "rb") as image:
        response = await client.post(
            f"/media_files/web_master/{web_master_task_in_progress['id']}",
            files={"media_file": ("sample.jpg", image, "image/jpeg")},
            headers=headers,
        )
    response.raise_for_status()
    file_id = response.json()["media_files_info"][0]["id"]
    yield web_master_task_in_progress["id"], file_id, headers
    await client.delete(
        f"/media_files/web_master/{web_master_task_in_progress['id']}",
        params={"file_id": file_id},
        headers=headers,
    )
