import uuid

import pytest_asyncio

from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.media_buyer]


@pytest_asyncio.fixture
async def media_buyer_team(admin_user, client):
    async def _create_team(prefix_pattern=None) -> tuple:
        uuid_str = uuid.uuid4().hex[:8]
        prefix = f"team_prefix_{uuid_str}" if prefix_pattern is None else prefix_pattern.format(uuid=uuid_str)
        name = f"team_{uuid_str}"
        resp = await client.post(
            "/admin/media_buyers_team/create",
            json={"name": name, "prefix": prefix, "custom_task_start_id": 100},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp.raise_for_status()
        team_data = resp.json()
        return team_data["id"], team_data["name"], team_data["prefix"]

    return _create_team


@pytest_asyncio.fixture
async def media_buyer_team_with_lead(admin_user, client, media_buyer_team, make_user):
    team_id, name, prefix = await media_buyer_team()
    lead_user = await make_user(UserRole.lead_media_buyer)
    await client.post(
        "/admin/media_buyers_team/add_lead",
        json={"team_id": team_id, "media_buyer_lead_id": lead_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    return team_id, name, prefix


@pytest_asyncio.fixture
async def media_buyer_team_with_member(request, admin_user, client, media_buyer_team, make_user, media_buyer_user):
    prefix_pattern = getattr(request, "param", None)
    team_id, name, prefix = await media_buyer_team(prefix_pattern=prefix_pattern)
    lead_user = await make_user(UserRole.lead_media_buyer)
    await client.post(
        "/admin/media_buyers_team/add_lead",
        json={"team_id": team_id, "media_buyer_lead_id": lead_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    await client.post(
        f"/admin/media_buyers_team/{team_id}/add_buyer",
        params={"buyer_id": media_buyer_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    return team_id, prefix, media_buyer_user["id"]
