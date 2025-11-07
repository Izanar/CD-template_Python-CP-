from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ENDPOINT = "/statistic/designers/points"
ALLOWED_ROLES = [UserRole.lead_designer, UserRole.admin, UserRole.designer]


@pytest.mark.asyncio
class TestGetDesignerPoints:
    async def test_points_calculation(
        self,
        client: AsyncClient,
        lead_designer_user: dict,
        designer_user: dict,
        make_tasks_with_points,
        clean_designer_tasks,
    ):
        await make_tasks_with_points(
            assigned_to_id=designer_user["id"],
            points=[1, 2],
        )

        resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"})
        assert resp.status_code == 200
        data = resp.json()
        stat = next(d for d in data["items"] if d["designer"]["id"] == designer_user["id"])
        assert stat["completed_tasks"] == 2
        assert stat["total_points"] == 3

    async def test_date_range_filter(
        self,
        client: AsyncClient,
        lead_designer_user: dict,
        designer_user: dict,
        make_tasks_with_points,
        make_designer_tasks,
        clean_designer_tasks,
    ):
        today = datetime.now(timezone.utc).date()
        date_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        await make_tasks_with_points(
            assigned_to_id=designer_user["id"],
            points=[1],
        )

        await make_designer_tasks(
            status=DesignerTaskStatus.IN_PROGRESS,
            count=1,
            assigned_to_id=designer_user["id"],
        )

        resp = await client.get(
            f"{ENDPOINT}?completed_from={date_from}&completed_to={date_to}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        stat = next(d for d in data["items"] if d["designer"]["id"] == designer_user["id"])
        assert stat["completed_tasks"] == 1
        assert stat["total_points"] == 1

    async def test_invalid_date_range_400(
        self,
        client: AsyncClient,
        lead_designer_user: dict,
    ):
        r = await client.get(
            f"{ENDPOINT}?completed_from=2025-05-30&completed_to=2025-05-25",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert r.status_code == 400
        assert "'completed_from' must be ≤ 'completed_to'" in r.text

    async def test_forbidden_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users: dict,
    ):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {user['access_token']}"})
            assert resp.status_code in (401, 403)
