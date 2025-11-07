import pytest
from httpx import AsyncClient

from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.task_type import DesignerTaskTypeEnum


@pytest.mark.asyncio
class TestDesignerTaskHistoryAfterActions:
    async def test_create_event_recorded(
        self,
        client: AsyncClient,
        new_task: dict,
        lead_designer_user: dict,
    ):
        task_id = new_task["id"]
        headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.get(f"/task_history/designer/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert any(item["event"] == TaskEvent.TASK.value and item["event_info"] == "created" for item in data)

    async def test_update_event_recorded(
        self,
        client: AsyncClient,
        new_draft_task: dict,
        media_buyer_user: dict,
        lead_designer_user: dict,
    ):
        task_id = new_draft_task["id"]
        buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.patch(
            f"/media_buyer/designer/{task_id}/update",
            json={
                "description": "updated history",
                "task_type": DesignerTaskTypeEnum.land_video.value,
            },
            headers=buyer_headers,
        )
        assert resp.status_code == 200, f"Update failed: {resp.status_code} {resp.text}"

        lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.get(f"/task_history/designer/{task_id}", headers=lead_headers)
        data = resp.json()

        assert any(item["event"] == TaskEvent.TASK.value and item["event_info"] == "updated" for item in data)

    async def test_send_event_recorded(
        self,
        client: AsyncClient,
        new_draft_task: dict,
        media_buyer_user: dict,
        lead_designer_user: dict,
    ):
        task_id = new_draft_task["id"]
        buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.patch(f"/media_buyer/designer/{task_id}/send", headers=buyer_headers)
        assert resp.status_code == 200, f"Send failed: {resp.status_code} {resp.text}"

        lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.get(f"/task_history/designer/{task_id}", headers=lead_headers)
        data = resp.json()

        assert any(
            item["event"] == TaskEvent.STATUS.value and item["event_info"] == DesignerTaskStatus.WAITING_TO_ASSIGN.value
            for item in data
        )

    async def test_request_edit_event_recorded(
        self,
        client: AsyncClient,
        new_task_under_review: dict,
        unsolved_edit: int,
        lead_designer_user: dict,
    ):
        task_id = new_task_under_review["id"]
        headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}

        resp = await client.get(f"/task_history/designer/{task_id}", headers=headers)
        data = resp.json()

        assert any(
            item["event"] == TaskEvent.STATUS.value and item["event_info"] == "requested_changes" for item in data
        )

    async def test_approve_edit_event_recorded(
        self,
        client: AsyncClient,
        new_task_under_review: dict,
        unsolved_edit: int,
        media_buyer_user: dict,
        lead_designer_user: dict,
        designer_user: dict,
    ):
        task_id = new_task_under_review["id"]

        designer_headers = {"Authorization": f"Bearer {designer_user['access_token']}"}
        await client.post(f"/designer/start_task/{task_id}", headers=designer_headers)
        await client.post(f"/designer/mark_task_as_done/{task_id}", headers=designer_headers)

        lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        await client.post(f"/lead_designer/task/{task_id}/approve", headers=lead_headers)

        buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}
        resp = await client.post(
            "/media_buyer/designer/approve_task_edit",
            json={"task_id": task_id, "edit_id": unsolved_edit},
            headers=buyer_headers,
        )
        assert resp.status_code == 200, f"Approve edit failed: {resp.status_code} {resp.text}"

        resp = await client.get(f"/task_history/designer/{task_id}", headers=lead_headers)
        data = resp.json()

        assert any(item["event"] == TaskEvent.EDIT.value and item["event_info"] == "approved" for item in data)

    async def test_approve_task_event_recorded(
        self,
        client: AsyncClient,
        new_task_under_review: dict,
        media_buyer_user: dict,
        lead_designer_user: dict,
    ):
        task_id = new_task_under_review["id"]
        buyer_headers = {"Authorization": f"Bearer {media_buyer_user['access_token']}"}

        resp = await client.post(f"/media_buyer/designer/{task_id}/approve", headers=buyer_headers, json={})
        assert resp.status_code == 200, f"Approve failed: {resp.status_code} {resp.text}"

        lead_headers = {"Authorization": f"Bearer {lead_designer_user['access_token']}"}
        resp = await client.get(f"/task_history/designer/{task_id}", headers=lead_headers)
        data = resp.json()

        assert any(item["event"] == TaskEvent.STATUS.value and item["event_info"] == "completed" for item in data)
