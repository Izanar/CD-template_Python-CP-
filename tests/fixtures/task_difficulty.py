import uuid
from typing import Any

import pytest


@pytest.fixture
def new_difficulty(admin_user, client):
    async def _create(name: str | None = None, points: int = 1) -> dict[str, Any]:
        payload = {
            "name": name or f"diff_{uuid.uuid4().hex[:8]}",
            "points": points,
        }
        resp = await client.post(
            "/admin/designer/tasks/create_difficulty",
            json=payload,
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp.raise_for_status()
        return resp.json()

    return _create


@pytest.fixture
def new_web_master_task_difficulty(admin_user, client):
    async def _create(name: str | None = None, points: int = 1) -> dict[str, Any]:
        payload = {
            "name": name or f"diff_{uuid.uuid4().hex[:8]}",
            "points": points,
        }
        resp = await client.post(
            "/admin/web_master/tasks/create_difficulty",
            json=payload,
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )
        resp.raise_for_status()
        return resp.json()

    return _create
