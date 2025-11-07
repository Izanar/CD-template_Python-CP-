import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer, UserRole.lead_media_buyer, UserRole.admin]

ENDPOINT = "/media_buyer/designer/approve_task_edit"


@pytest.mark.asyncio
class TestApproveTaskEdit:
    async def test_approve_success(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_task_under_review,
        unsolved_edit,
    ):
        headers = {"Authorization": "Bearer " + media_buyer_user["access_token"]}
        response = await client.post(
            ENDPOINT,
            json={"task_id": new_task_under_review["id"], "edit_id": unsolved_edit},
            headers=headers,
        )
        assert response.status_code == 200
        task_data = response.json()

        edit_objects = [edit for edit in task_data["edits"] if edit["id"] == unsolved_edit]
        assert edit_objects and edit_objects[0]["solved_at"] is not None
        assert response.json()["task_status"] == DesignerTaskStatus.UNDER_BUYER_REVIEW.value

    async def test_edit_not_found_returns_404(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_task_under_review,
    ):
        headers = {"Authorization": "Bearer " + media_buyer_user["access_token"]}
        response = await client.post(
            ENDPOINT,
            json={"task_id": new_task_under_review["id"], "edit_id": 999_999},
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Edit not found"

    async def test_edit_already_solved_returns_409(
        self,
        client: AsyncClient,
        media_buyer_user,
        new_task_under_review,
        unsolved_edit,
    ):
        headers = {"Authorization": "Bearer " + media_buyer_user["access_token"]}
        await client.post(
            ENDPOINT,
            json={"task_id": new_task_under_review["id"], "edit_id": unsolved_edit},
            headers=headers,
        )
        response = await client.post(
            ENDPOINT,
            json={"task_id": new_task_under_review["id"], "edit_id": unsolved_edit},
            headers=headers,
        )
        assert response.status_code == 409
        assert "Edit already solved" in response.json()["detail"]

    async def test_not_task_creator_returns_403(
        self,
        client: AsyncClient,
        make_user,
        new_task_under_review,
        unsolved_edit,
    ):
        other_buyer = await make_user(UserRole.media_buyer)
        headers = {"Authorization": "Bearer " + other_buyer["access_token"]}
        response = await client.post(
            ENDPOINT,
            json={"task_id": new_task_under_review["id"], "edit_id": unsolved_edit},
            headers=headers,
        )
        assert response.status_code == 403
        assert "did not create" in response.json()["detail"]

    async def test_access_restricted_roles(
        self,
        client: AsyncClient,
        restricted_users,
        new_task_under_review,
        unsolved_edit,
    ):
        for _, user in restricted_users(*ALLOWED_ROLES):
            headers = {"Authorization": "Bearer " + user["access_token"]}
            response = await client.post(
                ENDPOINT,
                json={"task_id": new_task_under_review["id"], "edit_id": unsolved_edit},
                headers=headers,
            )
            assert response.status_code in (401, 403, 409)
