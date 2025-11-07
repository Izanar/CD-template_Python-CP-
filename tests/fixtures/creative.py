import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def creative_with_approaches(
    client: AsyncClient,
    task_in_progress: dict,
    media_buyer_user: dict,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

    creative_data = {
        "task_id": task_in_progress["id"],
        "format": "vertical",
        "subtitles": True,
        "plashka": False,
        "text": "fixture text",
    }

    resp = await client.post(
        "/creatives/create",
        json=[creative_data],
        headers=headers,
    )
    resp.raise_for_status()

    creatives = resp.json()
    return creatives[0] if creatives else None


@pytest_asyncio.fixture
async def creative_without_approaches(
    client: AsyncClient,
    task_in_progress: dict,
    media_buyer_user: dict,
) -> dict:
    headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

    creative_data = {
        "task_id": task_in_progress["id"],
        "format": "vertical",
        "subtitles": True,
        "plashka": False,
        "text": None,
    }

    resp = await client.post(
        "/creatives/create",
        json=[creative_data],
        headers=headers,
    )
    resp.raise_for_status()

    creatives = resp.json()
    return creatives[0] if creatives else None
