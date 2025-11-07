import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestRemoveBuyerFromTeam:
    async def test_remove_buyer_success(
        self,
        admin_user,
        client,
        media_buyer_team_with_member,
    ):
        team_id, _prefix, buyer_id = media_buyer_team_with_member
        resp = await client.request(
            method="DELETE",
            url=f"/admin/media_buyers_team/{team_id}/remove_buyer",
            params={"buyer_id": buyer_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

    async def test_remove_buyer_not_in_team(self, admin_user, client, media_buyer_team_with_lead, media_buyer_user):
        team_id, _name, _prefix = media_buyer_team_with_lead
        resp = await client.delete(
            f"/admin/media_buyers_team/{team_id}/remove_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_nonexistent_team(self, admin_user, client, media_buyer_user):
        resp = await client.delete(
            "/admin/media_buyers_team/999999/remove_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_nonexistent_buyer(self, admin_user, client, media_buyer_team_with_member):
        team_id, _prefix, _buyer_id = media_buyer_team_with_member

        resp = await client.delete(
            f"/admin/media_buyers_team/{team_id}/remove_buyer",
            params={"buyer_id": 999999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_forbidden_for_non_admin(self, restricted_users, client, media_buyer_team_with_member):
        team_id, _prefix, buyer_id = media_buyer_team_with_member
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/media_buyers_team/{team_id}/remove_buyer",
                params={"buyer_id": buyer_id},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
