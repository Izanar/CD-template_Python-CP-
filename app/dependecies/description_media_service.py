from typing import Annotated

from fastapi import Depends

from app.dependecies.stub import DatabaseRepositoryStub, S3BucketStub
from app.repository.database.base import DatabaseRepository
from app.services.tasks.description_media import DescriptionMediaOnCreateService


def get_description_media_service(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    s3_bucket=Depends(S3BucketStub),
) -> DescriptionMediaOnCreateService:
    return DescriptionMediaOnCreateService(media_repo=db_repo.media_file, s3_bucket=s3_bucket)
