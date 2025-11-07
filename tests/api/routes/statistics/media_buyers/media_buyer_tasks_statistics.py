from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = (
    UserRole.lead_media_buyer,
    UserRole.lead_designer,
    UserRole.lead_web_master,
    UserRole.admin,
)


@pytest.mark.asyncio
class TestGetBuyersStatistics:
    endpoint = "/statistic/buyers_statistics"

    async def test_counts_include_completed(self, make_designer_tasks, client: AsyncClient, admin_user):
        await make_designer_tasks(status=DesignerTaskStatus.IN_PROGRESS, count=2)
        await make_designer_tasks(status=DesignerTaskStatus.COMPLETED, count=1)

        resp = await client.get(self.endpoint, headers={"Authorization": f"Bearer {admin_user['access_token']}"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["items"][0]["tasks_assigned"] == 3
        assert data["items"][0]["tasks_completed"] == 1

    async def test_date_range_filter(self, make_designer_tasks, client: AsyncClient, admin_user):
        now = datetime.now(timezone.utc)
        await make_designer_tasks(status=DesignerTaskStatus.IN_PROGRESS, created_at=now - timedelta(days=5))
        await make_designer_tasks(status=DesignerTaskStatus.IN_PROGRESS, created_at=now)

        resp = await client.get(
            self.endpoint,
            params={
                "start_date": (now.date() - timedelta(days=7)).isoformat(),
                "end_date": (now.date() - timedelta(days=1)).isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["tasks_assigned"] == 1

    async def test_pagination_limit_offset(self, make_user, make_designer_tasks, client: AsyncClient, admin_user):
        for _ in range(12):
            buyer = await make_user(role=UserRole.media_buyer)
            await make_designer_tasks(status=DesignerTaskStatus.IN_PROGRESS, created_by_id=buyer["id"])

        # Page 1
        resp1 = await client.get(
            self.endpoint,
            params={"limit": 5, "offset": 0},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["meta"]["limit"] == 5
        assert len(data1["items"]) == 5

        # Page 2
        resp2 = await client.get(
            self.endpoint,
            params={"limit": 5, "offset": 5},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["meta"]["current_page"] == 2
        assert len(data2["items"]) == 5
        assert {item["user"]["id"] for item in data1["items"]}.isdisjoint(
            {item["user"]["id"] for item in data2["items"]}
        )

    async def test_access_restricted_roles(self, client: AsyncClient, restricted_users):
        for _, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(self.endpoint, headers={"Authorization": f"Bearer {user['access_token']}"})
            assert resp.status_code in (401, 403), f"Expected 401/403 for role {user['role']}, got {resp.status_code}"
