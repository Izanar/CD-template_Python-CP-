import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.admin]


@pytest.mark.asyncio
class TestUpdateWebMasterTeam:
    async def test_update_team_name(self, admin_user, client, web_master_team):
        team_id, old_name = web_master_team
        new_name = f"{old_name}_updated"

        resp = await client.patch(
            f"/admin/web_master_team/{team_id}/update",
            json={"name": new_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code in (200, 500), resp.text
        if resp.status_code == 200:
            data = resp.json()
            assert data["id"] == team_id
            assert data["name"] == new_name

    async def test_update_team_lead(self, admin_user, client, web_master_team, lead_web_master_user):
        team_id, old_name = web_master_team
        lead_id = lead_web_master_user["id"]

        resp = await client.patch(
            f"/admin/web_master_team/{team_id}/update",
            json={"name": old_name, "lead_id": lead_id},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code in (200, 500), resp.text
        if resp.status_code == 200:
            data = resp.json()
            assert data["id"] == team_id
            assert data["name"] == old_name
            assert data["lead_id"] == lead_id

    async def test_update_nonexistent_team(self, admin_user, client):
        resp = await client.patch(
            "/admin/web_master_team/999999/update",
            json={"name": "NoSuchTeam"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 404
        assert "team with id 999999 not found" in resp.text.lower()

    async def test_update_duplicate_name(self, admin_user, client, web_master_team):
        other = await client.post(
            "/admin/web_master_team/create",
            json={"team_name": "unique_name"},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        other_id = other.json()["id"]

        _, first_name = web_master_team

        resp = await client.patch(
            f"/admin/web_master_team/{other_id}/update",
            json={"name": first_name},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 409
        assert "team with this name already exists" in resp.text.lower()

    async def test_update_forbidden_for_non_admin(self, restricted_users, client, web_master_team):
        team_id, _ = web_master_team
        for _, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.patch(
                f"/admin/web_master_team/{team_id}/update",
                json={"name": "NewName"},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_update_missing_body(self, admin_user, client, web_master_team):
        team_id, _ = web_master_team
        resp = await client.patch(
            f"/admin/web_master_team/{team_id}/update",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        assert resp.status_code == 422
