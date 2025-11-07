from datetime import date
from typing import Literal

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import and_, case, delete, exists, func, insert, or_, select, update
from sqlalchemy.orm import selectinload

from app.models import (
    Admin,
    Designer,
    DesignersTeamMembers,
    DesignerTask,
    Geo,
    MediaBuyer,
    MediaBuyersTeam,
    MediaBuyersTeamMembers,
    User,
    WebMaster,
)
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.tasks.designer_tasks.utils import get_geo_by_id, resolve_geo
from app.repository.user.base import UserBaseRepository
from app.repository.utils import build_order_by
from app.schemas.enums.user import UserRole
from app.schemas.media_buyers.tasks.designer_tasks import GeoResponseSchema
from app.schemas.user import UserCreateSchema, UserUpdateSchema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRepository(UserBaseRepository, DatabaseEngineRepository):
    async def get_current_user(self, username: str):
        async with self.session_maker() as db:
            role = (await db.execute(select(User.role).where(User.username == username))).scalar_one_or_none()
            if role is None:
                return None

            role_options = {
                UserRole.designer: selectinload(User.designer).selectinload(Designer.teams),
                UserRole.lead_designer: selectinload(User.designer).selectinload(Designer.teams),
                UserRole.web_master: selectinload(User.web_master).selectinload(WebMaster.teams),
                UserRole.lead_web_master: selectinload(User.web_master).selectinload(WebMaster.teams),
                UserRole.media_buyer: selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
                UserRole.lead_media_buyer: selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
            }

            stmt = select(User).where(User.username == username)

            if option := role_options.get(role):
                stmt = stmt.options(option)

            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_users(
        self,
        limit: int,
        offset: int,
        role: str | None = None,
        has_team: bool | None = None,
        order_by: str | None = None,
        order_direction: Literal["asc", "desc"] | None = None,
        created_at: date | None = None,
        team_id: int | None = None,
        media_buyer_team_id: int | None = None,
        username: str | None = None,
    ):
        async with self.session_maker() as db:
            filters = []
            team_filter_applied = False

            if role:
                filters.append(User.role == role)

            if has_team is not None:
                in_team = or_(
                    exists(
                        select(1)
                        .select_from(MediaBuyersTeamMembers)
                        .where(MediaBuyersTeamMembers.media_buyer_id == User.id)
                    ),
                    exists(
                        select(1).select_from(DesignersTeamMembers).where(DesignersTeamMembers.designer_id == User.id)
                    ),
                )

                if has_team is False and team_id is not None:
                    in_specific_team = or_(
                        exists(
                            select(1)
                            .select_from(MediaBuyersTeamMembers)
                            .where(
                                (MediaBuyersTeamMembers.media_buyer_id == User.id)
                                & (MediaBuyersTeamMembers.team_id == team_id)
                            )
                        ),
                        exists(
                            select(1)
                            .select_from(DesignersTeamMembers)
                            .where(
                                (DesignersTeamMembers.designer_id == User.id)
                                & (DesignersTeamMembers.team_id == team_id)
                            )
                        ),
                    )
                    filters.append(or_(~in_team, in_specific_team))
                    team_filter_applied = True
                else:
                    filters.append(in_team if has_team else ~in_team)

            if created_at:
                filters.append(func.date(User.created_at) == created_at)

            if team_id is not None and not team_filter_applied:
                filters.append(
                    or_(
                        exists(
                            select(1)
                            .select_from(MediaBuyersTeamMembers)
                            .where(
                                (MediaBuyersTeamMembers.media_buyer_id == User.id)
                                & (MediaBuyersTeamMembers.team_id == team_id)
                            )
                        ),
                        exists(
                            select(1)
                            .select_from(DesignersTeamMembers)
                            .where(
                                (DesignersTeamMembers.designer_id == User.id)
                                & (DesignersTeamMembers.team_id == team_id)
                            )
                        ),
                    )
                )

            if media_buyer_team_id:
                designer_id_stmt = select(MediaBuyersTeam.responsible_designer).where(
                    MediaBuyersTeam.id == media_buyer_team_id
                )
                designer_user_id = await db.scalar(designer_id_stmt)

                filters.append(User.id.in_([designer_user_id] if designer_user_id else []))

            if username:
                filters.append(User.username.ilike(f"%{username}%"))

            count_stmt = select(func.count()).select_from(User).where(*filters)
            total_result = await db.execute(count_stmt)
            total_count = total_result.scalar_one()

            stmt = (
                select(User)
                .options(
                    selectinload(User.designer).selectinload(Designer.teams),
                    selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
                    selectinload(User.designer).selectinload(Designer.responsible_for_teams),
                )
                .where(*filters)
                .limit(limit)
                .offset(offset)
            )

            if order_by:
                stmt = build_order_by(stmt, User, order_by, order_direction)
            else:
                order_parts = [User.created_at.desc(), User.id.desc()]
                if has_team is False and team_id is not None:
                    in_specific_team = or_(
                        exists(
                            select(1)
                            .select_from(MediaBuyersTeamMembers)
                            .where(
                                MediaBuyersTeamMembers.media_buyer_id == User.id,
                                MediaBuyersTeamMembers.team_id == team_id,
                            )
                        ),
                        exists(
                            select(1)
                            .select_from(DesignersTeamMembers)
                            .where(
                                DesignersTeamMembers.designer_id == User.id,
                                DesignersTeamMembers.team_id == team_id,
                            )
                        ),
                    )
                    priority = case(
                        (in_specific_team, 0),
                        else_=1,
                    )
                    order_parts.insert(0, priority.asc())

                stmt = stmt.order_by(*order_parts)
            result = await db.execute(stmt)
            users = result.scalars().all()
            for user in users:
                if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer) and user.media_buyer:
                    user.allow_view_team_tasks = user.media_buyer.allow_view_team_tasks
            return users, total_count

    async def get_user(self, user_id: int):
        async with self.session_maker() as db:
            if user := await db.scalar(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.media_buyer).selectinload(MediaBuyer.teams))
            ):
                if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer) and user.media_buyer:
                    user.allow_view_team_tasks = user.media_buyer.allow_view_team_tasks
                return user
            raise HTTPException(status_code=404, detail="User does not exist")

    async def create_user(self, user: UserCreateSchema):
        db_mapping = {
            "admin": Admin,
            "media_buyer": MediaBuyer,
            "web_master": WebMaster,
            "lead_web_master": WebMaster,
            "lead_media_buyer": MediaBuyer,
            "lead_designer": Designer,
            "designer": Designer,
        }

        async with self.session_maker() as db:
            if await db.scalar(select(User).where(User.username == user.username)):
                raise HTTPException(status_code=400, detail="Username is already in use")

            allow_view_team_tasks = user.allow_view_team_tasks

            hashed_password = pwd_context.hash(user.password)
            user_data = user.model_dump(exclude={"allow_view_team_tasks"})
            user_data["password"] = hashed_password
            result = await db.execute(
                insert(User).values(**user_data).returning(User).options(selectinload(User.media_buyer))
            )
            user = result.scalar_one()

            role_model = db_mapping[user.role.name.lower()]
            role_data = {"id": user.id}
            if role_model == MediaBuyer:
                role_data["allow_view_team_tasks"] = allow_view_team_tasks or False

            await db.execute(insert(role_model).values(**role_data))
            await db.commit()
            user = await self.get_user(user_id=user.id)
            if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer):
                user.allow_view_team_tasks = user.media_buyer.allow_view_team_tasks
            return user

    async def update_user(self, user: UserUpdateSchema, user_id: int):
        async with self.session_maker() as db:
            db_user = await self.get_user(user_id)

            update_data = user.model_dump(exclude_unset=True)

            if "password" in update_data:
                update_data["password"] = pwd_context.hash(update_data["password"])

            if "username" in update_data and await db.scalar(
                select(User).where(User.username == update_data["username"], User.id != user_id)
            ):
                raise HTTPException(400, "Username is already in use")

            if "allow_view_team_tasks" in update_data:
                if db_user.role != UserRole.lead_media_buyer:
                    raise HTTPException(400, "Flag allowed only for lead_media_buyer")
                await db.execute(
                    update(MediaBuyer)
                    .where(MediaBuyer.id == user_id)
                    .values(allow_view_team_tasks=update_data.pop("allow_view_team_tasks"))
                )

            if update_data:
                await db.execute(update(User).where(User.id == user_id).values(update_data))

            await db.commit()

        user = await self.get_user(user_id=user_id)
        if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer):
            user.allow_view_team_tasks = user.media_buyer.allow_view_team_tasks
        return user

    async def delete_user(self, user_id: int):
        async with self.session_maker() as db:
            await self.get_user(user_id=user_id)

            deleted_user = await db.execute(delete(User).where(User.id == user_id).returning(User))

            await db.commit()
            return deleted_user.scalar()

    async def logout_user(self, user_id: int):
        async with self.session_maker() as db:
            result = await db.execute(update(User).where(User.id == user_id).values(jwt_version=User.jwt_version + 1))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            await db.commit()

    async def logout_all_users(self):
        async with self.session_maker() as db:
            await db.execute(update(User).values(jwt_version=User.jwt_version + 1))
            await db.commit()

    async def create_geo(self, code: str) -> GeoResponseSchema:
        code_u, name = resolve_geo(code)

        async with self.session_maker() as session:
            stmt = select(Geo).where(Geo.code == code_u)
            geo_obj = await session.scalar(stmt)

            if geo_obj:
                if geo_obj.is_deleted:
                    geo_obj.is_deleted = False
                    geo_obj.name = name
                    await session.commit()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Geo code already exists",
                    )
            else:
                geo_obj = Geo(code=code_u, name=name)
                session.add(geo_obj)
                await session.commit()

            await session.refresh(geo_obj)
            return GeoResponseSchema.model_validate(geo_obj)

    async def delete_geo(self, geo_id: int) -> None:
        async with self.session_maker() as session:
            geo = await get_geo_by_id(session, geo_id)
            geo.is_deleted = True
            await session.commit()

    async def get_all_geos(self, context: Literal["create", "filter"]) -> list[Geo]:
        async with self.session_maker() as session:
            if context == "create":
                predicate = Geo.is_deleted.is_(False)
            else:
                tasks_exist = exists(select(1).where(DesignerTask.geo_id == Geo.id))
                predicate = or_(Geo.is_deleted.is_(False), and_(Geo.is_deleted.is_(True), tasks_exist))

            stmt = select(Geo).where(predicate).order_by(Geo.name)
            return (await session.scalars(stmt)).all()
