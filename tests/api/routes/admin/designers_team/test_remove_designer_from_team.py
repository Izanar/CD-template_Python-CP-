import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestRemoveDesignerFromTeam:
    async def test_remove_designer_success(self, admin_user, client, team_with_member):
        team_id, member_id = team_with_member
        del_resp = await client.delete(
            f"/admin/designers_team/{team_id}/remove_designer",
            params={"designer_id": member_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert del_resp.status_code == 200

    async def test_remove_designer_not_in_team(self, admin_user, client, lead_designer_user, designer_user):
        create_resp = await client.post(
            "/admin/designers_team/create",
            json={"team_name": "EmptyTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        team_id = create_resp.json()["id"]
        await client.post(
            "/admin/designers_team/add_lead",
            json={"team_id": team_id, "lead_id": lead_designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp = await client.delete(
            f"/admin/designers_team/{team_id}/remove_designer",
            params={"designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (400, 404)
        assert "not in team" in resp.text.lower()

    async def test_remove_from_nonexistent_team(self, admin_user, client, designer_user):
        resp = await client.delete(
            "/admin/designers_team/999999/remove_designer",
            params={"designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_remove_forbidden_for_non_admin(self, restricted_users, client, new_team):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.delete(
                f"/admin/designers_team/{new_team}/remove_designer",
                params={"designer_id": 1},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
