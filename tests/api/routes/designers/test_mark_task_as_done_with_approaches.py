import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMarkTaskAsDoneWithApproaches:
    endpoint = "/designer/mark_task_as_done/{task_id}"

    async def test_mark_done_without_approaches_fails(
        self, client: AsyncClient, admin_user, designer_file, creative_without_approaches
    ):
        task_id, _file_id, _headers = designer_file
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}

        resp = await client.post(self.endpoint.format(task_id=task_id), headers=headers)
        assert resp.status_code == 409
        assert "approaches" in resp.json()["detail"].lower()

    async def test_mark_done_with_approaches_succeeds(
        self, client: AsyncClient, admin_user, designer_user, designer_file, creative_without_approaches
    ):
        task_id, _file_id, _headers = designer_file

        creative_id = creative_without_approaches["id"]
        update_data = {"approaches": ["arrest", "cry", "scam"]}
        designer_headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        await client.patch(
            f"/creatives/{creative_id}",
            json=update_data,
            headers=designer_headers,
        )

        admin_headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        resp = await client.post(self.endpoint.format(task_id=task_id), headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["task_status"] == "under_tl_review"

    async def test_creative_approaches_are_sorted_correctly(
        self, client: AsyncClient, media_buyer_user, designer_user, task_in_progress
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        creative_data = {
            "task_id": task_in_progress["id"],
            "format": "vertical",
            "subtitles": True,
            "plashka": False,
        }

        resp = await client.post(
            "/creatives/create",
            json=[creative_data],
            headers=headers,
        )
        resp.raise_for_status()

        creative = resp.json()[0]
        creative_id = creative["id"]

        update_data = {"approaches": ["scam", "arrest", "cry", "interview"]}
        designer_headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp = await client.patch(
            f"/creatives/{creative_id}",
            json=update_data,
            headers=designer_headers,
        )
        resp.raise_for_status()

        updated_creative = resp.json()
        expected_order = ["arrest", "cry", "scam", "interview"]
        assert updated_creative["approaches"] == expected_order

    async def test_creative_approaches_empty_list_works(self, client: AsyncClient, media_buyer_user, task_in_progress):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        creative_data = {
            "task_id": task_in_progress["id"],
            "format": "vertical",
            "subtitles": True,
            "plashka": False,
        }

        resp = await client.post(
            "/creatives/create",
            json=[creative_data],
            headers=headers,
        )
        resp.raise_for_status()

        creative = resp.json()[0]
        assert creative["approaches"] == []

    async def test_creative_update_approaches_works(
        self, client: AsyncClient, designer_user, creative_without_approaches
    ):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        creative_id = creative_without_approaches["id"]

        update_data = {"approaches": ["counter", "crisis", "arrest"], "text": "updated text"}

        resp = await client.patch(
            f"/creatives/{creative_id}",
            json=update_data,
            headers=headers,
        )
        resp.raise_for_status()

        creative = resp.json()

        expected_order = ["arrest", "counter", "crisis"]
        assert creative["approaches"] == expected_order
        assert creative.get("text") == "updated text"

    async def test_creative_update_invalid_approaches_validation(
        self, client: AsyncClient, designer_user, creative_without_approaches
    ):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        creative_id = creative_without_approaches["id"]

        update_data = {"approaches": ["invalid_approach", "arrest"]}

        resp = await client.patch(
            f"/creatives/{creative_id}",
            json=update_data,
            headers=headers,
        )
        assert resp.status_code == 422
        assert "Input should be" in resp.json()["detail"][0]["msg"]
