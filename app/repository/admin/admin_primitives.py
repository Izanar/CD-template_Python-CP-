from typing import Literal, Type

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select

from app.models import Base, Celebrity, Funnel, Language, SiteName, WebMasterTask
from app.repository.engine.database import DatabaseEngineRepository


class AdminPrimitivesRepository(DatabaseEngineRepository):
    async def create_primitive(self, model: Type[Base], name: str):
        async with self.session_maker() as session:
            name_lower = name.lower()
            stmt = select(model).where(func.lower(model.name) == name_lower)
            obj = await session.scalar(stmt)

            if obj:
                if obj.is_deleted:
                    obj.is_deleted = False
                    obj.name = name
                    await session.commit()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{model.__tablename__.replace('_', ' ').title()} with this name already exists",
                    )
            else:
                obj = model(name=name)
                session.add(obj)
                await session.commit()

            await session.refresh(obj)
            return obj

    async def delete_primitive(self, model: Type[Base], obj_id: int):
        async with self.session_maker() as session:
            obj = await session.get(model, obj_id)
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__tablename__.replace('_', ' ').title()} not found",
                )
            obj.is_deleted = True
            await session.commit()

    async def get_all_primitives(self, model: Type[Base], fk_column, context: Literal["create", "filter"]):
        async with self.session_maker() as session:
            if context == "create":
                predicate = model.is_deleted.is_(False)
            else:
                tasks_exist = exists(select(1).where(fk_column == model.id))
                predicate = or_(model.is_deleted.is_(False), and_(model.is_deleted.is_(True), tasks_exist))

            stmt = select(model).where(predicate).order_by(model.name)
            result = await session.scalars(stmt)
            return result.all()

    async def create_funnel(self, name: str):
        return await self.create_primitive(Funnel, name)

    async def delete_funnel(self, funnel_id: int):
        await self.delete_primitive(Funnel, funnel_id)

    async def get_all_funnels(self, context: Literal["create", "filter"]):
        return await self.get_all_primitives(Funnel, WebMasterTask.funnel_id, context)

    async def create_site_name(self, name: str):
        return await self.create_primitive(SiteName, name)

    async def delete_site_name(self, site_name_id: int):
        await self.delete_primitive(SiteName, site_name_id)

    async def get_all_site_names(self, context: Literal["create", "filter"]):
        return await self.get_all_primitives(SiteName, WebMasterTask.site_name_id, context)

    async def create_celebrity(self, name: str):
        return await self.create_primitive(Celebrity, name)

    async def delete_celebrity(self, celebrity_id: int):
        await self.delete_primitive(Celebrity, celebrity_id)

    async def get_all_celebrities(self, context: Literal["create", "filter"]):
        return await self.get_all_primitives(Celebrity, WebMasterTask.celebrity_id, context)

    async def create_language(self, name: str, code: str):
        from app.repository.admin.utils import check_language_conflicts

        async with self.session_maker() as session:
            existing = await check_language_conflicts(session, name, code)
            if existing:
                return existing

            language = Language(name=name, code=code)
            session.add(language)
            await session.commit()
            await session.refresh(language)
            return language

    async def delete_language(self, language_id: int):
        await self.delete_primitive(Language, language_id)

    async def get_all_languages(self):
        async with self.session_maker() as session:
            stmt = select(Language).where(Language.is_deleted.is_(False)).order_by(Language.name)
            result = await session.scalars(stmt)
            return result.all()
