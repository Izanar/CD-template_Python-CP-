from typing import List

from fastapi import HTTPException
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import selectinload

from app.models import Creative, DesignerTask, DesignerTaskCelebrity, MediaFile
from app.repository.creative.adname_utils import check_adname_uniqueness, rename_creative_files_to_adname
from app.repository.creative.base import CreativeBaseRepository
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.tasks.designer_tasks.utils import get_task_by_id
from app.repository.media_file.utils import check_creative_media_file_exists
from app.schemas.creative import CreativeCreateSchema, CreativeUpdateSchema
from app.schemas.enums.creative_approach import CreativeApproach


class CreativeRepository(CreativeBaseRepository, DatabaseEngineRepository):
    async def create_creatives_batch(self, creatives_data: List[CreativeCreateSchema], task_id: int) -> List[Creative]:
        async with self.session_maker() as db:
            await get_task_by_id(db, task_id)

            creative_values = []
            for creative_data in creatives_data:
                creative_values.append(
                    {
                        "task_id": task_id,
                        "format": creative_data.format,
                        "subtitles": creative_data.subtitles,
                        "plashka": creative_data.plashka,
                        "text": creative_data.text,
                    }
                )

            statement = insert(Creative).values(creative_values).returning(Creative)
            result = await db.execute(statement)
            created_creatives = result.scalars().all()
            await db.commit()

            creative_ids = [creative.id for creative in created_creatives]
            statement = (
                select(Creative).where(Creative.id.in_(creative_ids)).options(selectinload(Creative.media_files))
            )
            result = await db.execute(statement)
            return result.scalars().all()

    async def get_creative_by_id(self, creative_id: int) -> Creative:
        async with self.session_maker() as db:
            statement = (
                select(Creative)
                .where(Creative.id == creative_id)
                .options(
                    selectinload(Creative.media_files),
                    selectinload(Creative.task).selectinload(DesignerTask.created_by),
                )
            )
            result = await db.execute(statement)
            creative = result.scalar_one_or_none()
            if not creative:
                raise HTTPException(status_code=404, detail=f"Creative with ID {creative_id} not found")
            return creative

    async def add_creative_files(self, creative_id: int, file_keys: List[str], s3_bucket) -> None:
        async with self.session_maker() as db:
            creative = await self.get_creative_by_id(creative_id)

            if len(creative.media_files) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Creative already has a media file. One creative can have only one media file.",
                )

            if not file_keys:
                raise HTTPException(status_code=400, detail="At least one file key is required")

            if len(file_keys) > 1:
                raise HTTPException(status_code=400, detail="Only one media file is allowed per creative")

            file_key = file_keys[0]
            file_url = await s3_bucket.construct_url(file_key)

            statement = insert(MediaFile).values(
                {"creative_id": creative_id, "file_key": file_key, "file_url": file_url, "is_description": False}
            )
            await db.execute(statement)
            await db.commit()

    async def update_creative_fields(
        self, creative_id: int, update_data: CreativeUpdateSchema, s3_bucket=None
    ) -> Creative:
        async with self.session_maker() as db:
            # Prepare update values
            update_values = {key: value for key, value in update_data.model_dump().items() if value is not None}

            if "approaches" in update_values:
                update_values["approach"] = CreativeApproach.sort_approaches(update_values["approaches"])
                del update_values["approaches"]

            if "ad_name" in update_values:
                ad_name = update_values["ad_name"]
                await check_adname_uniqueness(ad_name, creative_id, db)

                if s3_bucket:
                    current_creative = await self.get_creative_by_id(creative_id)
                    await rename_creative_files_to_adname(current_creative, ad_name, s3_bucket, db)

            if update_values:
                statement = update(Creative).where(Creative.id == creative_id).values(**update_values)
                await db.execute(statement)

            await db.commit()
            return await self.get_creative_by_id(creative_id)

    async def get_task_creatives(self, task_id: int) -> List[Creative]:
        async with self.session_maker() as db:
            statement = select(Creative).where(Creative.task_id == task_id).options(selectinload(Creative.media_files))
            result = await db.execute(statement)
            return result.scalars().all()

    async def get_creative_by_ad_name(self, ad_name: str) -> Creative:
        async with self.session_maker() as db:
            statement = (
                select(Creative)
                .where(Creative.ad_name == ad_name)
                .options(
                    selectinload(Creative.media_files),
                    selectinload(Creative.task)
                    .selectinload(DesignerTask.celebrity_relations)
                    .selectinload(DesignerTaskCelebrity.celebrity),
                )
            )
            result = await db.execute(statement)
            creative = result.scalar_one_or_none()
            if not creative:
                raise HTTPException(status_code=404, detail=f"Creative with ad_name {ad_name} not found")

            return creative

    async def update_creative_media_file(
        self, creative_id: int, file_id: int, new_file_key: str, s3_bucket
    ) -> Creative:
        async with self.session_maker() as db:
            creative = await self.get_creative_by_id(creative_id)
            await check_creative_media_file_exists(creative, file_id)

            new_file_url = await s3_bucket.construct_url(new_file_key)

            statement = (
                update(MediaFile).where(MediaFile.id == file_id).values(file_key=new_file_key, file_url=new_file_url)
            )
            await db.execute(statement)
            await db.commit()

            return await self.get_creative_by_id(creative_id)

    async def delete_creative_media_file(self, creative_id: int, file_id: int, s3_bucket) -> Creative:
        async with self.session_maker() as db:
            creative = await self.get_creative_by_id(creative_id)
            await check_creative_media_file_exists(creative, file_id)

            statement = delete(MediaFile).where(MediaFile.id == file_id)
            await db.execute(statement)
            await db.commit()

            return await self.get_creative_by_id(creative_id)
