import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestRemoveResponsibleDesigner:
    async def test_remove_responsible_designer_success(
        self,
        admin_user,
        client,
        media_buyer_team_with_lead,
        designer_user,
    ):
        team_id, _name, _prefix = media_buyer_team_with_lead

        await client.post(
            "/admin/media_buyers_team/add_responsible_designer",
            params={"team_id": team_id, "responsible_designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        resp = await client.request(
            method="DELETE",
            url="/admin/media_buyers_team/remove_responsible_designer",
            params={"team_id": team_id, "responsible_designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200, resp.text

    async def test_remove_responsible_designer_nonexistent_team(self, admin_user, client):
        resp = await client.delete(
            "/admin/media_buyers_team/remove_responsible_designer",
            params={"team_id": 999999, "responsible_designer_id": 1},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_responsible_designer_forbidden_for_non_admin(
        self, restricted_users, client, media_buyer_team
    ):
        team_id, _, _ = await media_buyer_team()

        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                "/admin/media_buyers_team/remove_responsible_designer",
                params={"team_id": team_id, "responsible_designer_id": 1},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_remove_responsible_designer_validation_error(self, admin_user, client):
        resp = await client.delete(
            "/admin/media_buyers_team/remove_responsible_designer",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
