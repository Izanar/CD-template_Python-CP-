import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddLeadMediaBuyerTeam:
    async def test_add_lead_success(self, admin_user, client, media_buyer_team, lead_media_buyer_user):
        team_id, _, _ = await media_buyer_team()
        resp = await client.post(
            "/admin/media_buyers_team/add_lead",
            json={"team_id": team_id, "media_buyer_lead_id": lead_media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == team_id
        assert any(m["id"] == lead_media_buyer_user["id"] for m in data["members_list"])

    async def test_add_lead_forbidden_for_non_admin(self, restricted_users, client, media_buyer_team, media_buyer_user):
        team_id, _, _ = await media_buyer_team()
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                "/admin/media_buyers_team/add_lead",
                json={"team_id": team_id, "media_buyer_lead_id": media_buyer_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_add_lead_missing_body(self, admin_user, client):
        resp = await client.post(
            "/admin/media_buyers_team/add_lead",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
