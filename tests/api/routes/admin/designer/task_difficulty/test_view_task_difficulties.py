import pytest

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [
    UserRole.media_buyer,
    UserRole.lead_media_buyer,
    UserRole.designer,
    UserRole.lead_designer,
    UserRole.admin,
]


@pytest.mark.asyncio
class TestViewTaskDifficulties:
    async def test_view_difficulties_success(self, new_difficulty, admin_user, client):
        first = await new_difficulty(name="easy", points=5)
        second = await new_difficulty(name="hard", points=20)

        resp = await client.get(
            "/admin/designer/tasks/view_difficulties",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert isinstance(payload, list)
        ids = {item["id"] for item in payload}
        assert {first["id"], second["id"]}.issubset(ids)

        sample = next(item for item in payload if item["id"] == first["id"])
        assert sample == {
            "id": first["id"],
            "name": "easy",
            "points": 5,
        }

    async def test_view_difficulties_forbidden_for_non_allowed_roles(self, restricted_users, client):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(
                "/admin/designer/tasks/view_difficulties",
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)
