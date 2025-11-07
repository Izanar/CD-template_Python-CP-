import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreateCreatives:
    endpoint = "/creatives/create"

    async def test_create_creatives_with_text(
        self,
        client: AsyncClient,
        media_buyer_user,
        task_in_progress: dict,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        creative_payload = [
            {
                "task_id": task_in_progress["id"],
                "format": "vertical",
                "subtitles": True,
                "plashka": False,
                "text": "Direct create: sample text",
            }
        ]

        resp = await client.post(self.endpoint, json=creative_payload, headers=headers)
        resp.raise_for_status()

        data = resp.json()
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["task_id"] == task_in_progress["id"]
        assert data[0]["text"] == "Direct create: sample text"
