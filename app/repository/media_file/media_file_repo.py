from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute

from app.models import MediaFile
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_file.base import MediaFileBaseRepository


class MediaFileRepository(MediaFileBaseRepository, DatabaseEngineRepository):
    async def _add_image(self, task_id: int, file_url: str, key_field) -> None:
        async with self.session_maker() as db:
            try:
                await db.execute(insert(MediaFile).values({key_field.key: task_id, "file_url": file_url}))
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(404, "Task does not exist")

    async def _update_image(
        self, task_id: int, new_file_url: str, file_id: int, key_field: InstrumentedAttribute
    ) -> None:
        async with self.session_maker() as db:
            stmt = update(MediaFile).where(key_field == task_id, MediaFile.id == file_id).values(file_url=new_file_url)
            await db.execute(stmt)
            await db.commit()

    async def _delete_image(self, task_id: int, file_id: int, key_field: InstrumentedAttribute) -> None:
        async with self.session_maker() as db:
            stmt = delete(MediaFile).where(key_field == task_id, MediaFile.id == file_id)
            await db.execute(stmt)
            await db.commit()

    async def add_web_master_task_image(self, task_id: int, file_url: str) -> None:
        await self._add_image(task_id=task_id, file_url=file_url, key_field=MediaFile.web_master_task_id)

    async def update_web_master_task_image(self, task_id: int, file_id: int, new_file_url: str) -> None:
        await self._update_image(
            task_id=task_id, new_file_url=new_file_url, file_id=file_id, key_field=MediaFile.web_master_task_id
        )

    async def delete_web_master_task_image(
        self,
        task_id: int,
        file_id: int,
    ) -> None:
        await self._delete_image(task_id=task_id, file_id=file_id, key_field=MediaFile.web_master_task_id)

    async def add_designer_task_image(self, task_id: int, file_url: str) -> None:
        await self._add_image(task_id=task_id, file_url=file_url, key_field=MediaFile.designer_task_id)

    async def update_designer_task_image(self, task_id: int, file_id: int, new_file_url: str) -> None:
        await self._update_image(
            task_id=task_id, new_file_url=new_file_url, file_id=file_id, key_field=MediaFile.designer_task_id
        )

    async def delete_designer_task_image(self, task_id: int, file_id: int) -> None:
        await self._delete_image(task_id=task_id, file_id=file_id, key_field=MediaFile.designer_task_id)

    async def get_file_by_id(self, file_id: int) -> MediaFile:
        async with self.session_maker() as db:
            if media_file := await db.scalar(select(MediaFile).where(MediaFile.id == file_id)):
                return media_file
            raise HTTPException(status_code=404, detail="File not found")

    async def _bulk_insert(
        self,
        task_id: int,
        file_keys: Sequence[str],
        key_field: InstrumentedAttribute,
        s3_bucket,
        is_description: bool = False,
    ) -> None:
        unique_keys = [k for k in dict.fromkeys(file_keys) if k]
        if not unique_keys:
            return

        rows = [
            {
                key_field.key: task_id,
                "file_key": k,
                "file_url": await s3_bucket.construct_url(k),
                "is_description": is_description,
            }
            for k in unique_keys
        ]
        async with self.session_maker() as db:
            await db.execute(insert(MediaFile), rows)
            await db.commit()

    async def _bulk_delete(
        self,
        task_id: int,
        file_ids: Sequence[int],
        key_field: InstrumentedAttribute,
    ) -> None:
        if not file_ids:
            return

        async with self.session_maker() as db:
            stmt = delete(MediaFile).where(key_field == task_id, MediaFile.id.in_(file_ids)).returning(MediaFile.id)
            result = await db.execute(stmt)
            await db.commit()

            deleted = [row[0] for row in result]
            missed = set(file_ids) - set(deleted)
            if missed:
                raise HTTPException(
                    status_code=404,
                    detail=f"Files not found: {list(missed)}",
                )

    async def _update_image_extra(
        self,
        task_id: int,
        file_id: int,
        new_file_key: str,
        key_field: InstrumentedAttribute,
        s3_bucket,
    ) -> None:
        if not new_file_key:
            raise HTTPException(422, "new_file_key must be non-empty")

        new_url = await s3_bucket.construct_url(new_file_key)

        async with self.session_maker() as db:
            stmt = (
                update(MediaFile)
                .where(key_field == task_id, MediaFile.id == file_id)
                .values(file_key=new_file_key, file_url=new_url)
            )
            result = await db.execute(stmt)
            await db.commit()

            if result.rowcount == 0:
                raise HTTPException(404, "File not found or not attached to task")

    async def update_designer_task_image_key(
        self,
        task_id: int,
        file_id: int,
        new_file_key: str,
        s3_bucket,
    ) -> None:
        await self._update_image_extra(task_id, file_id, new_file_key, MediaFile.designer_task_id, s3_bucket)

    async def add_designer_task_images(
        self,
        task_id: int,
        file_keys: list[str],
        s3_bucket,
        is_description: bool = False,
    ) -> None:
        await self._bulk_insert(task_id, file_keys, MediaFile.designer_task_id, s3_bucket, is_description)

    async def delete_designer_task_images(self, task_id: int, file_ids: list[int]) -> None:
        await self._bulk_delete(task_id, file_ids, MediaFile.designer_task_id)
