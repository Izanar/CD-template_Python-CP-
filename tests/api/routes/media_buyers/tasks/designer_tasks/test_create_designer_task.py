import pytest
from httpx import AsyncClient

from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer]


@pytest.mark.asyncio
class TestCreateDesignerTask:
    endpoint = "/media_buyer/designer/create"

    async def test_create_task_as_media_buyer(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        celebrity_1,
        celebrity_2,
    ):
        payload = {
            "description": "Happy-path task",
            "task_type": DesignerTaskTypeEnum.land_video.value,
            "celebrities": [celebrity_1["id"], celebrity_2["id"]],
        }
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["description"] == payload["description"]
        assert data["task_type"] == DesignerTaskTypeEnum.land_video.value
        assert "celebrities" in data
        assert len(data["celebrities"]) == 2
        assert {c["id"] for c in data["celebrities"]} == {celebrity_1["id"], celebrity_2["id"]}

    async def test_create_task_with_invalid_task_type(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        payload = {"description": "Bad type", "task_type": "invalid_type"}
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code == 422  # Validation error for invalid enum value

    async def test_create_task_without_team(
        self,
        client: AsyncClient,
        make_user,
    ):
        fresh_buyer = await make_user(UserRole.media_buyer)
        headers = {"Authorization": f"Bearer {fresh_buyer['access_token']}"}
        payload = {"description": "Buyer without team", "task_type": DesignerTaskTypeEnum.land_video.value}
        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code == 404
        assert "Team ID not found" in resp.json()["detail"]

    async def test_access_restricted_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for role, user in restricted_users(*ALLOWED_ROLES):
            payload = {"description": f"Denied for {role}", "task_type": DesignerTaskTypeEnum.land_video.value}
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.post(self.endpoint, json=payload, headers=headers)
            assert resp.status_code in (401, 403, 404)

    @pytest.mark.parametrize("media_buyer_team_with_member", [None, "prefix1.2_{uuid}"], indirect=True)
    async def test_task_title_correctness(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
    ):
        team_id, prefix, _ = media_buyer_team_with_member
        payload = {"description": "Test task title", "task_type": DesignerTaskTypeEnum.land_video.value}
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == f"{prefix}.100"

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == f"{prefix}.101"

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == f"{prefix}.102"

    async def test_create_task_with_creatives_text(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
    ):
        payload = {
            "description": "Task with creatives text",
            "task_type": DesignerTaskTypeEnum.land_video.value,
            "creatives": [
                {
                    "format": "vertical",
                    "subtitles": True,
                    "plashka": False,
                    "text": "Hook: arrest, then counter!",
                }
            ],
        }
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.post(self.endpoint, json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "creatives" in data
        assert isinstance(data["creatives"], list)
        assert len(data["creatives"]) == 1
        assert data["creatives"][0]["text"] == "Hook: arrest, then counter!"
