import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddBuyerToTeam:
    async def test_add_buyer_success(
        self,
        admin_user,
        client,
        media_buyer_team_with_lead,
        media_buyer_user,
    ):
        team_id, _, prefix = media_buyer_team_with_lead

        resp = await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert any(m["id"] == media_buyer_user["id"] for m in data["members_list"])

    async def test_add_buyer_without_lead(self, admin_user, client, media_buyer_team, media_buyer_user):
        team_id, _, _ = await media_buyer_team()
        resp = await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        # TODO: Change to 403 when lead is required
        assert resp.status_code == 403
        # TODO: assert "no lead" in resp.text.lower()

    async def test_add_buyer_nonexistent_team(self, admin_user, client, media_buyer_user):
        resp = await client.post(
            "/admin/media_buyers_team/999999/add_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_nonexistent_buyer(self, admin_user, client, media_buyer_team_with_lead):
        team_id, _, prefix = media_buyer_team_with_lead
        resp = await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": 999999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_wrong_role(self, admin_user, client, media_buyer_team_with_lead, designer_user):
        team_id, _, prefix = media_buyer_team_with_lead
        resp = await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 400
        assert "not a media buyer" in resp.text.lower()

    async def test_add_duplicate(
        self,
        admin_user,
        client,
        media_buyer_team_with_lead,
        media_buyer_user,
    ):
        team_id, _, prefix = media_buyer_team_with_lead
        await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp = await client.post(
            f"/admin/media_buyers_team/{team_id}/add_buyer",
            params={"buyer_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 409
        assert "already in team" in resp.text.lower()

    async def test_add_forbidden_for_non_admin(
        self, restricted_users, client, media_buyer_team_with_lead, media_buyer_user
    ):
        team_id, _, prefix = media_buyer_team_with_lead
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                f"/admin/media_buyers_team/{team_id}/add_buyer",
                params={"buyer_id": media_buyer_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
