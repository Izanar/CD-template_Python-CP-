from fastapi import HTTPException
from sqlalchemy import select, update

from app.models import Creative, MediaFile


async def check_adname_uniqueness(ad_name: str, creative_id: int, db_session) -> None:
    existing_creative_stmt = select(Creative).where(Creative.ad_name == ad_name, Creative.id != creative_id)
    existing_creative = await db_session.scalar(existing_creative_stmt)
    if existing_creative:
        raise HTTPException(status_code=400, detail="Ad name already exists")


async def rename_creative_files_to_adname(creative, ad_name: str, s3_bucket, db_session) -> None:
    if not creative.media_files:
        return

    for media_file in creative.media_files:
        if media_file.file_key:
            try:
                new_file_key, new_file_url = await s3_bucket.rename_file_to_adname(media_file.file_key, ad_name)

                media_update_stmt = (
                    update(MediaFile)
                    .where(MediaFile.id == media_file.id)
                    .values(file_key=new_file_key, file_url=new_file_url)
                )
                await db_session.execute(media_update_stmt)

            except FileNotFoundError:
                pass
