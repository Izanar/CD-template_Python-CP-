import uuid

import pytest_asyncio


@pytest_asyncio.fixture
async def web_master_team(admin_user, client):
    team_name = f"team_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/admin/web_master_team/create",
        json={"team_name": team_name},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()
    body = resp.json()
    return body["id"], body["name"]


@pytest_asyncio.fixture
async def web_master_team_with_lead(admin_user, client, lead_web_master_user, web_master_team):
    team_id, team_name = web_master_team

    resp = await client.post(
        "/admin/web_master_team/add_lead",
        json={"team_id": team_id, "lead_id": lead_web_master_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()
    return team_id, team_name


@pytest_asyncio.fixture
async def web_master_team_with_member(admin_user, client, web_master_team_with_lead, web_master_user):
    team_id, _ = web_master_team_with_lead

    resp = await client.post(
        f"/admin/web_master_team/{team_id}/add_web_master",
        params={"web_master_id": web_master_user["id"]},
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    resp.raise_for_status()
    return team_id, web_master_user["id"]
