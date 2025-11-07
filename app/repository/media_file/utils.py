from pathlib import Path
from typing import Sequence

from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def validate_file_size(file: UploadFile):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE_MB} MB limit")

    file.file.seek(0)  # Reset file pointer to the beginning


ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz"}


def is_archive_key(s3_key: str) -> bool:
    return Path(s3_key.split("?")[0]).suffix.lower() in ARCHIVE_EXT


async def check_archives_permission(task, file_keys: Sequence[str]) -> None:
    if not any(is_archive_key(k) for k in file_keys):
        return

    team = task.buyer_team
    if not team or not team.allow_archives:
        raise HTTPException(403, "Archives are not allowed for this team")


async def ensure_files_exist(keys: list[str], s3_bucket) -> None:
    bucket = await s3_bucket.s3.Bucket(s3_bucket.bucket_name)

    for key in keys:
        if not key:
            continue
        obj = await bucket.Object(key.lstrip("/"))
        try:
            await obj.load()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                raise HTTPException(status_code=422, detail=f"Temp file not found: {key}")
            raise


async def check_creative_media_file_exists(creative, file_id: int):
    media_file = next((mf for mf in creative.media_files or [] if mf.id == file_id), None)
    if not media_file:
        raise HTTPException(status_code=404, detail=f"Media file with ID {file_id} not found for this creative")
    return media_file
