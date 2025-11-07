from operator import itemgetter

import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin, UserRole.lead_designer]

ENDPOINT = "/statistic/designers"


@pytest.mark.asyncio
class TestGetDesignerTaskStatistic:
    async def test_get_designer_task_statistic_success(
        self,
        client: AsyncClient,
        lead_designer_user: dict,
        designer_user: dict,
        make_designer_tasks,
        clean_designer_tasks,
    ):
        await make_designer_tasks(DesignerTaskStatus.WAITING_TO_START, assigned_to_id=designer_user["id"])
        await make_designer_tasks(DesignerTaskStatus.IN_PROGRESS, assigned_to_id=designer_user["id"])
        await make_designer_tasks(DesignerTaskStatus.UNDER_TL_REVIEW, assigned_to_id=designer_user["id"])
        await make_designer_tasks(DesignerTaskStatus.REQUESTED_CHANGES, assigned_to_id=designer_user["id"])
        await make_designer_tasks(DesignerTaskStatus.UNDER_BUYER_REVIEW, assigned_to_id=designer_user["id"])

        resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"})
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}, response: {resp.text}"

        payload = resp.json()
        assert "items" in payload and "meta" in payload
        items = payload["items"]

        designer_stats = next((d for d in items if d["designer"]["id"] == designer_user["id"]), None)
        assert designer_stats is not None, "Stats for designer not found"

        assert itemgetter(
            "waiting_to_start_count",
            "in_progress_count",
            "under_tl_review_count",
            "requested_changes_count",
            "under_buyer_review_count",
        )(designer_stats) == (1, 1, 1, 1, 1)

    async def test_get_designer_task_statistic_forbidden_for_restricted_users(
        self, client: AsyncClient, restricted_users: dict
    ):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {user['access_token']}"})
            assert resp.status_code in (401, 403), f"Unexpected status {resp.status_code} for role {_role}"

    async def test_get_designers_returns_empty_list_for_nonexistent_team_id(
        self, lead_designer_user, client: AsyncClient
    ):
        resp = await client.get(
            f"{ENDPOINT}?team_id=999999", headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == [], f"Expected empty list, got {data['items']}"
        assert data["meta"]["total"] == 0
