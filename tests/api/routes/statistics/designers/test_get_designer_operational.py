import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ENDPOINT = "/statistic/designers/operational_tasks"
ALLOWED_ROLES = [UserRole.lead_designer, UserRole.admin]


@pytest.mark.asyncio
class TestGetDesignerOperationalTasks:
    async def test_get_operational_tasks_statistic(
        self,
        client: AsyncClient,
        make_tasks_with_operational,
        lead_designer_user: dict,
        media_buyer_user: dict,
        clean_designer_tasks,
    ):
        statuses = [
            DesignerTaskStatus.WAITING_TO_ASSIGN,
            DesignerTaskStatus.WAITING_TO_START,
            DesignerTaskStatus.IN_PROGRESS,
            DesignerTaskStatus.REQUESTED_CHANGES,
            DesignerTaskStatus.UNDER_TL_REVIEW,
            DesignerTaskStatus.COMPLETED,
        ]

        for status in statuses:
            await make_tasks_with_operational(
                status=status, assigned_to_id=None, count=1, created_by_id=media_buyer_user["id"]
            )

        response = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"})
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, response: {response.text}"

        data = response.json()

        assert data["waiting_to_assign"] == 1
        assert data["waiting_to_start"] == 1
        assert data["in_progress"] == 1
        assert data["requested_changes"] == 1
        assert data["under_tl_review"] == 1
        assert data["completed"] == 1

    async def test_forbidden_for_other_roles(
        self,
        client: AsyncClient,
        restricted_users: dict,
    ):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {user['access_token']}"})
            assert resp.status_code in (401, 403)
