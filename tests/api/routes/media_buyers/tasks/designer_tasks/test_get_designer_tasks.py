import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = (
    UserRole.media_buyer,
    UserRole.lead_media_buyer,
    UserRole.designer,
    UserRole.lead_designer,
    UserRole.admin,
)


@pytest.mark.asyncio
class TestGetDesignerTasks:
    endpoint = "/media_buyer/designer/tasks"

    async def test_get_tasks_default_pagination(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
        new_draft_task,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        response = await client.get(
            self.endpoint,
            params={"limit": 100, "offset": 0},
            headers=headers,
        )
        assert response.status_code == 200

        result = response.json()
        task_ids = {item["id"] for item in result["items"]}
        assert new_task["id"] in task_ids
        assert new_draft_task["id"] in task_ids

    async def test_get_tasks_with_limit_offset(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
        new_draft_task,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp1 = await client.get(self.endpoint, params={"limit": 1, "offset": 0}, headers=headers)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["meta"]["limit"] == 1
        assert len(data1["items"]) == 1

        resp2 = await client.get(self.endpoint, params={"limit": 1, "offset": 1}, headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["meta"]["current_page"] == 2
        assert len(data2["items"]) == 1
        assert data1["items"][0]["id"] != data2["items"][0]["id"]

    async def test_filter_by_status_and_type(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        # Create tasks with the "string" task type
        draft_task_resp = await client.post(
            "/media_buyer/designer/create_draft",
            json={"description": "draft task", "task_type": DesignerTaskTypeEnum.land_video.value},
            headers=headers,
        )
        draft_task_resp.raise_for_status()
        draft_task = draft_task_resp.json()

        task_resp = await client.post(
            "/media_buyer/designer/create",
            json={"description": "regular task", "task_type": DesignerTaskTypeEnum.land_video.value},
            headers=headers,
        )
        task_resp.raise_for_status()
        task = task_resp.json()

        # Test filtering by status
        resp_status = await client.get(
            self.endpoint,
            params={"task_status": DesignerTaskStatus.DRAFT.value},
            headers=headers,
        )
        assert resp_status.status_code == 200
        ids_status = {t["id"] for t in resp_status.json()["items"]}
        assert draft_task["id"] in ids_status
        assert task["id"] not in ids_status

        # Test filtering by task_type enum
        resp_type = await client.get(
            self.endpoint, params={"task_type": DesignerTaskTypeEnum.land_video.value}, headers=headers
        )
        assert resp_type.status_code == 200
        ids_type = {t["id"] for t in resp_type.json()["items"]}
        assert draft_task["id"] in ids_type
        assert task["id"] in ids_type

    async def test_invalid_order_by_returns_400(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.get(
            self.endpoint,
            params={"order_by": "nonexistent_field"},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_invalid_task_type_enum_returns_422(
        self,
        client: AsyncClient,
        media_buyer_user,
    ):
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.get(
            self.endpoint,
            params={"task_type": "nonexistent_type"},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_lead_designer_can_use_team_filters(
        self,
        client: AsyncClient,
        lead_designer_user,
    ):
        headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.get(
            self.endpoint,
            params={"is_media_buyers_teams": True},
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_designer_without_permissions_gets_400(
        self,
        client: AsyncClient,
        designer_user,
    ):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
        resp = await client.get(
            self.endpoint,
            params={"is_media_buyers_teams": True},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Only lead designers can filter by media buyer teams or assignment" in resp.json()["detail"]

    async def test_access_restricted_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": f"Bearer {user['access_token']}"}
            resp = await client.get(self.endpoint, headers=headers)
            assert resp.status_code in (401, 403)

    async def test_sort_by_title(self, client: AsyncClient, designer_user):
        h = {"Authorization": f"Bearer {designer_user['access_token']}"}
        r = await client.get(
            self.endpoint,
            params={"order_by": "title", "order_direction": "asc", "limit": 20},
            headers=h,
        )
        assert r.status_code == 200
        titles = [t["title"].lower() for t in r.json()["items"]]
        assert titles == sorted(titles)

    async def test_sort_by_difficulty_points(self, client: AsyncClient, designer_user):
        h = {"Authorization": f"Bearer {designer_user['access_token']}"}
        r = await client.get(
            self.endpoint,
            params={"order_by": "difficulty_points", "order_direction": "desc", "limit": 20},
            headers=h,
        )
        assert r.status_code == 200
        points = [max((d["points"] for d in t["difficulties"]), default=0) for t in r.json()["items"]]
        assert points == sorted(points, reverse=True)

    async def test_filter_by_difficulty_ids_designer(self, client: AsyncClient, designer_user):
        h = {"Authorization": f"Bearer {designer_user['access_token']}"}

        r_all = await client.get(self.endpoint, headers=h)
        assert r_all.status_code == 200
        task_with_diff = next((t for t in r_all.json()["items"] if t["difficulties"]), None)
        if not task_with_diff:
            pytest.skip("No tasks with difficulties found")

        diff_id = task_with_diff["difficulties"][0]["id"]

        r = await client.get(self.endpoint, params={"difficulty_ids": [diff_id]}, headers=h)
        assert r.status_code == 200
        assert all(diff_id in [d["id"] for d in t["difficulties"]] for t in r.json()["items"])

    async def test_filter_by_difficulty_ids_forbidden(self, client: AsyncClient, media_buyer_user):
        h = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        r = await client.get(self.endpoint, params={"difficulty_ids": [1]}, headers=h)
        assert r.status_code == 400
        assert "available only for designers" in r.json()["detail"]

    async def test_filter_by_ad_name(
        self,
        client: AsyncClient,
        media_buyer_user,
        media_buyer_team_with_member,
        new_task,
        test_creative_with_data,
        test_creative_minimal,
    ):
        """Test filtering tasks by ad_name in creatives"""
        headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        # Тест с точным совпадением
        response = await client.get(
            self.endpoint,
            params={"ad_name": "test_creative_api", "limit": 100, "offset": 0},
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["items"]) >= 1
        # Проверяем, что в результатах есть задачи с креативами, содержащими нужный ad_name
        task_ids = {item["id"] for item in result["items"]}
        assert new_task["id"] in task_ids

        # Тест с частичным совпадением
        response = await client.get(
            self.endpoint,
            params={"ad_name": "test_creative", "limit": 100, "offset": 0},
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["items"]) >= 1  # Должны найти хотя бы один креатив

        # Тест с несуществующим ad_name
        response = await client.get(
            self.endpoint,
            params={"ad_name": "nonexistent_ad", "limit": 100, "offset": 0},
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["items"]) == 0

        # Тест с пустым ad_name (должен вернуть все задачи)
        response = await client.get(
            self.endpoint,
            params={"ad_name": "", "limit": 100, "offset": 0},
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["items"]) >= 1
