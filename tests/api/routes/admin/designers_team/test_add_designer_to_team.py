import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestAddDesignerToTeam:
    async def test_add_designer_success(self, admin_user, client, team_with_lead, designer_user):
        team_id = team_with_lead
        add_resp = await client.post(
            f"/admin/designers_team/{team_id}/add_designer",
            params={"designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert add_resp.status_code == 200, add_resp.text
        data = add_resp.json()
        assert data["id"] == team_id
        assert any(m["id"] == designer_user["id"] for m in data["members_list"]), (
            f"Designer {designer_user['id']} not in members_list: {data['members_list']}"
        )

    async def test_add_designer_no_lead(self, admin_user, client, new_team, make_user):
        designer_user = await make_user(role=UserRole.designer)
        resp = await client.post(
            f"/admin/designers_team/{new_team}/add_designer",
            params={"designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 200

    async def test_add_to_nonexistent_team(self, admin_user, client, designer_user):
        resp = await client.post(
            "/admin/designers_team/999999/add_designer",
            params={"designer_id": designer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404

    async def test_add_nonexistent_designer(self, admin_user, client, team_with_lead):
        team_id = team_with_lead
        resp = await client.post(
            f"/admin/designers_team/{team_id}/add_designer",
            params={"designer_id": 999999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code in (400, 404)

    async def test_add_designer_duplicate(self, admin_user, client, team_with_member):
        team_id, member_id = team_with_member
        second = await client.post(
            f"/admin/designers_team/{team_id}/add_designer",
            params={"designer_id": member_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert second.status_code in (400, 404)
        assert "already in team" in second.text.lower()

    async def test_add_forbidden_for_non_admin(self, restricted_users, client, new_team, designer_user):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.post(
                f"/admin/designers_team/{new_team}/add_designer",
                params={"designer_id": designer_user["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
