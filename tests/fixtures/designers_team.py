import uuid

import pytest_asyncio

from app.schemas.enums.user import UserRole


@pytest_asyncio.fixture
async def new_team(admin_user, client):
    team_name = f"team_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/admin/designers_team/create",
        json={"team_name": team_name},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


@pytest_asyncio.fixture
async def team_with_lead(admin_user, client, make_user, new_team):
    new_lead_designer = await make_user(UserRole.lead_designer)
    resp = await client.post(
        "/admin/designers_team/add_lead",
        json={"team_id": new_team, "lead_id": [new_lead_designer["id"]]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()

    return new_team


@pytest_asyncio.fixture
async def team_with_member(admin_user, client, team_with_lead, make_user):
    new_designer_user = await make_user(UserRole.designer)
    resp = await client.post(
        f"/admin/designers_team/{team_with_lead}/add_designer",
        params={"designer_id": new_designer_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()
    return team_with_lead, new_designer_user["id"]
