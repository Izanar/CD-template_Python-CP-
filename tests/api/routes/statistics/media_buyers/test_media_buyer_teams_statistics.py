import asyncio

import pytest
from httpx import AsyncClient

from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole

ALLOWED_ROLES = [UserRole.lead_designer, UserRole.admin]
ENDPOINT = "/statistic/media_buyer/teams"

STATUSES_NEEDED = (
    DesignerTaskStatus.WAITING_TO_ASSIGN,
    DesignerTaskStatus.WAITING_TO_START,
    DesignerTaskStatus.IN_PROGRESS,
    DesignerTaskStatus.REQUESTED_CHANGES,
    DesignerTaskStatus.UNDER_TL_REVIEW,
    DesignerTaskStatus.UNDER_BUYER_REVIEW,
)


def flatten(resp_json: dict) -> list[dict]:
    verticals = resp_json["items"]
    return [team for v in verticals for team in v["teams"]]


@pytest.mark.asyncio
class TestGetMediaBuyerTeamsStatistics:
    async def test_success_single_team(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_media_buyer_teams,
        make_designer_tasks,
    ):
        [(team_id, buyer_id)] = await make_media_buyer_teams()

        await asyncio.gather(*[make_designer_tasks(s, created_by_id=buyer_id) for s in STATUSES_NEEDED])
        await make_designer_tasks(DesignerTaskStatus.COMPLETED, 3, created_by_id=buyer_id)

        resp = await client.get(
            f"{ENDPOINT}?team_id={team_id}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        teams = flatten(resp.json())
        assert len(teams) == 1 and teams[0]["team_id"] == team_id

    async def test_filter_by_team_id(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_media_buyer_teams,
        make_designer_tasks,
    ):
        (team1_id, buyer_id), (team2_id, _) = await make_media_buyer_teams(count=2)

        await make_designer_tasks(DesignerTaskStatus.DRAFT, created_by_id=buyer_id, buyer_team_id=team2_id)
        await make_designer_tasks(DesignerTaskStatus.WAITING_TO_START, created_by_id=buyer_id, buyer_team_id=team1_id)

        resp = await client.get(
            f"{ENDPOINT}?team_id={team2_id}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        teams = flatten(resp.json())
        assert len(teams) == 1
        t2 = teams[0]
        assert t2["team_id"] == team2_id
        assert all(t2[s.value] == 0 for s in STATUSES_NEEDED)

        resp = await client.get(
            f"{ENDPOINT}?team_id={team1_id}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        teams = flatten(resp.json())
        assert len(teams) == 1
        t1 = teams[0]
        assert t1["team_id"] == team1_id
        assert t1["waiting_to_start"] == 1

    async def test_multiple_teams_statistics(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_media_buyer_teams,
        make_designer_tasks,
    ):
        (t1, b1), (t2, b2), (t3, b3) = await make_media_buyer_teams(count=3)

        await make_designer_tasks(DesignerTaskStatus.WAITING_TO_START, 2, created_by_id=b1, buyer_team_id=t1)
        await make_designer_tasks(DesignerTaskStatus.IN_PROGRESS, 1, created_by_id=b2, buyer_team_id=t2)
        await make_designer_tasks(DesignerTaskStatus.UNDER_BUYER_REVIEW, 4, created_by_id=b3, buyer_team_id=t3)

        resp = await client.get(
            ENDPOINT,
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        data = {t["team_id"]: t for t in flatten(resp.json())}

        assert data[t1]["waiting_to_start"] == 2
        assert data[t2]["in_progress"] == 1
        assert data[t3]["under_buyer_review"] == 4

    async def test_empty_response_when_no_tasks(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_media_buyer_teams,
    ):
        [(team_id, _)] = await make_media_buyer_teams(add_member=False)

        resp = await client.get(
            f"{ENDPOINT}?team_id={team_id}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        teams = flatten(resp.json())
        assert len(teams) == 1
        team = teams[0]
        assert team["team_id"] == team_id
        assert all(team[s.value] == 0 for s in STATUSES_NEEDED)

    async def test_delete_team_with_tasks_is_returned(
        self,
        client: AsyncClient,
        lead_designer_user,
        make_media_buyer_teams,
        make_designer_tasks,
    ):
        [(team_id, buyer_id)] = await make_media_buyer_teams()

        await make_designer_tasks(
            DesignerTaskStatus.WAITING_TO_ASSIGN, 2, created_by_id=buyer_id, buyer_team_id=team_id
        )

        resp = await client.get(
            f"{ENDPOINT}?team_id={team_id}",
            headers={"Authorization": f"Bearer {lead_designer_user['access_token']}"},
        )
        assert resp.status_code == 200
        teams = flatten(resp.json())
        assert len(teams) == 1
        team = teams[0]
        assert team["team_id"] == team_id
        assert team["waiting_to_assign"] == 2

    async def test_forbidden_for_restricted_roles(
        self,
        client: AsyncClient,
        restricted_users,
    ):
        for _role, user in restricted_users(*ALLOWED_ROLES):
            resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {user['access_token']}"})
            assert resp.status_code in (401, 403)
