import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUpdateDesignersTeam:
    @pytest.mark.parametrize("new_name", ["TeamOneUpdated", "Y123", "New Name"])
    async def test_update_team_success(self, admin_user, client, new_team, new_name):
        update_resp = await client.patch(
            f"/admin/designers_team/{new_team}/update",
            json={"name": new_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()
        assert data["id"] == new_team
        assert data["name"] == new_name

    async def test_update_nonexistent_team(self, admin_user, client):
        resp = await client.patch(
            "/admin/designers_team/999999/update",
            json={"name": "DoesNotExist"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Team with id 999999 not found"

    async def test_update_duplicate_name(self, admin_user, client):
        resp1 = await client.post(
            "/admin/designers_team/create",
            json={"team_name": "FirstTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp1.status_code in (200, 201), resp1.text
        team1 = resp1.json()

        resp2 = await client.post(
            "/admin/designers_team/create",
            json={"team_name": "SecondTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp2.status_code in (200, 201), resp2.text
        team2 = resp2.json()

        dup_resp = await client.patch(
            f"/admin/designers_team/{team2['id']}/update",
            json={"name": team1["name"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert dup_resp.status_code == 409
        assert "team with this name already exists" in dup_resp.text.lower()

    async def test_update_forbidden_for_non_admin(self, restricted_users, client, new_team):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.patch(
                f"/admin/designers_team/{new_team}/update",
                json={"name": "NewName"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_update_missing_body(self, admin_user, client, new_team):
        resp = await client.patch(
            f"/admin/designers_team/{new_team}/update",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
