import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import MediaBuyer, User
from app.repository.media_buyers.assistant.utils import get_keitaro_username_for_media_buyer
from app.schemas.enums.user import UserRole


@pytest.mark.asyncio
class TestSetAssistant:
    async def test_set_assistant_success(self, admin_user, client: AsyncClient, media_buyer_user, make_user, engine):
        assistant = await make_user(UserRole.media_buyer)

        resp = await client.post(
            "/admin/media_buyer/assistant/",
            json={"teacher_id": media_buyer_user["id"], "assistant_id": assistant["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == media_buyer_user["id"]
        assert data["username"] == media_buyer_user["username"]

        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as db:
            assistant_in_db = await db.scalar(select(MediaBuyer).where(MediaBuyer.id == assistant["id"]))
            assert assistant_in_db.assistant_reference_id == media_buyer_user["id"]

    async def test_set_assistant_self_reference(self, admin_user, client: AsyncClient, media_buyer_user):
        resp = await client.post(
            "/admin/media_buyer/assistant/",
            json={"teacher_id": media_buyer_user["id"], "assistant_id": media_buyer_user["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 400
        assert "cannot be their own assistant" in resp.json()["detail"]

    async def test_set_assistant_not_found(self, admin_user, client: AsyncClient, media_buyer_user):
        resp = await client.post(
            "/admin/media_buyer/assistant/",
            json={"teacher_id": media_buyer_user["id"], "assistant_id": 99999},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 404
        assert "Assistant not found" in resp.json()["detail"]

    async def test_set_assistant_forbidden_for_non_admin(
        self, restricted_users, client: AsyncClient, media_buyer_user, make_user
    ):
        assistant = await make_user(UserRole.media_buyer)

        for _, user in restricted_users(UserRole.admin):
            resp = await client.post(
                "/admin/media_buyer/assistant/",
                json={"teacher_id": media_buyer_user["id"], "assistant_id": assistant["id"]},
                headers={"Authorization": f"Bearer {user['access_token']}"},
            )
            assert resp.status_code in (401, 403)

    async def test_keitaro_username_with_assistant(
        self, admin_user, client: AsyncClient, media_buyer_user, make_user, engine
    ):
        assistant = await make_user(UserRole.media_buyer)

        await client.post(
            "/admin/media_buyer/assistant/",
            json={"teacher_id": media_buyer_user["id"], "assistant_id": assistant["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as db:
            # Check that assistant now uses teacher's username
            assistant_user = await db.get(User, assistant["id"])
            username = await get_keitaro_username_for_media_buyer(db, assistant_user)
            assert username == media_buyer_user["username"]

            # Check that teacher still uses their own username
            teacher_user = await db.get(User, media_buyer_user["id"])
            teacher_username = await get_keitaro_username_for_media_buyer(db, teacher_user)
            assert teacher_username == media_buyer_user["username"]

    async def test_keitaro_username_without_assistant(self, admin_user, client: AsyncClient, media_buyer_user, engine):
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as db:
            existing = await db.scalar(select(MediaBuyer).where(MediaBuyer.id == media_buyer_user["id"]))
            if not existing:
                await db.execute(
                    MediaBuyer.__table__.insert().values(id=media_buyer_user["id"], allow_view_team_tasks=False)
                )
            else:
                await db.execute(
                    MediaBuyer.__table__.update()
                    .where(MediaBuyer.id == media_buyer_user["id"])
                    .values(assistant_reference_id=None)
                )
            await db.commit()

            user = await db.get(User, media_buyer_user["id"])
            username = await get_keitaro_username_for_media_buyer(db, user)
            assert username == media_buyer_user["username"]

    async def test_user_response_always_original_username(
        self, admin_user, client: AsyncClient, media_buyer_user, make_user
    ):
        assistant = await make_user(UserRole.media_buyer)

        await client.post(
            "/admin/media_buyer/assistant/",
            json={"teacher_id": media_buyer_user["id"], "assistant_id": assistant["id"]},
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        resp = await client.get(
            f"/admin/user/{media_buyer_user['id']}",
            headers={"Authorization": f"Bearer {admin_user['access_token']}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == media_buyer_user["username"]
        assert data["username"] != assistant["username"]
