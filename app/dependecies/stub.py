import os
import re
from abc import ABC, abstractmethod
from typing import Any

from botocore.client import BaseClient
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

from app.models import DesignerTask, WebMasterTask
from app.repository.media_file.utils import validate_file_size

load_dotenv()


class Stub:
    """
    Stub class for FastAPI DI system,
    which allows to use `Depends` without any real dependencies in the code.
    """


class BaseInject(ABC):
    """
    A base abstract class for dependency injection.

    The `BaseInject` class should be inherited by other classes that provide specific implementations of dependency
    injection.
    The inherited classes should implement the `__call__` method with the desired logic for the injection.

    Notes:
    - This class is an abstract base class and should not be instantiated directly.
    - The `__call__` method should be implemented by inheriting classes.
    - The return type of the `__call__` method should be specified in the implementation as specified by the `->
    Any` type hint.
    """

    @abstractmethod
    async def __call__(self) -> Any:
        pass


class InjectStatic(BaseInject):
    """Class for injecting static values into an async function."""

    def __init__(self, target: Any) -> None:
        self.target = target

    async def __call__(self) -> Any:
        return self.target


class InjectContextManager(BaseInject):
    """Class for injecting value from context manager into an async function."""

    def __init__(self, target: Any) -> None:
        self.target = target

    async def __call__(self) -> Any:
        async with self.target() as value:
            yield value


class AppConfigStub(Stub):
    pass


class DatabaseStub(Stub):
    pass


class SessionStub(Stub):
    pass


class DatabaseRepositoryStub(Stub):
    pass


class S3BucketStub(Stub):
    pass


class NotificationServiceStub(Stub):
    pass


class InjectS3Resource(BaseInject):
    """Инъекция S3-ресурса через контекстный менеджер."""

    def __init__(self, session: BaseClient, bucket_name: str):
        self.session = session
        self.bucket_name = bucket_name
        self.s3 = None

    async def __call__(self):
        async with self.session.resource("s3") as s3:
            self.s3 = s3
            yield self

    async def upload_image(self, media_file: UploadFile, task_info: DesignerTask | WebMasterTask) -> str:
        """Метод загрузки изображения в S3."""
        await validate_file_size(file=media_file)
        env = os.getenv("ENV", "dev")
        safe_title = re.sub(r"\s+", "_", task_info.title)
        identifier = task_info.uuid if task_info.uuid is not None else task_info.id

        file_key = f"uploads/{env}/{identifier}/{safe_title}_{media_file.filename}"

        bucket = await self.s3.Bucket(self.bucket_name)
        await bucket.put_object(Key=file_key, Body=await media_file.read(), ContentType=media_file.content_type)

        return f"https://{self.bucket_name}.s3.amazonaws.com/{file_key}"

    async def construct_url(self, file_key: str) -> str:
        return f"https://{self.bucket_name}.s3.amazonaws.com/{file_key.lstrip('/')}"

    async def copy_object(self, src_key: str, dest_key: str) -> str:
        """Копирует объект внутри того же bucket-а. Возвращает финальный URL."""
        src = src_key.lstrip("/")
        dst = dest_key.lstrip("/")
        bucket = await self.s3.Bucket(self.bucket_name)
        obj = await bucket.Object(dst)
        await obj.copy({"Bucket": self.bucket_name, "Key": src})
        return await self.construct_url(dst)

    async def promote_temp_key(self, temp_key: str, env: str, task_uuid: str) -> tuple[str, str]:
        """
        Переносит /tmp/{env}/{rand_uuid}/{filename} → {env}/{task_uuid}/{filename}
        Возвращает пару (final_key, final_url).
        """
        filename = os.path.basename(temp_key)
        final_key = f"uploads/{env}/{task_uuid}/{filename}"
        final_url = await self.copy_object(temp_key, final_key)
        return final_key, final_url

    async def delete_image(self, file_url: str) -> bool:
        """Метод видалення зображення з S3."""
        file_key = file_url.split(f"https://{self.bucket_name}.s3.amazonaws.com/")[-1]

        bucket = await self.s3.Bucket(self.bucket_name)
        s3_object = await bucket.Object(file_key)
        delete_response = await s3_object.delete()

        if delete_response is None:
            raise HTTPException(status_code=404, detail="Image deletion failed")

        return True

    async def update_image(
        self, old_file_url: str, new_media_file: UploadFile, task_info: DesignerTask | WebMasterTask
    ) -> str:
        """Метод обновления изображения: удаляет старый файл и загружает новый."""
        await self.delete_image(file_url=old_file_url)
        return await self.upload_image(media_file=new_media_file, task_info=task_info)

    async def file_exists(self, file_key: str) -> bool:
        try:
            bucket = await self.s3.Bucket(self.bucket_name)
            obj = await bucket.Object(file_key)
            await obj.load()
            return True
        except Exception:
            return False

    async def rename_file_to_adname(self, old_file_key: str, ad_name: str) -> tuple[str, str]:
        if not await self.file_exists(old_file_key):
            raise FileNotFoundError(f"File {old_file_key} does not exist on S3")

        file_extension = os.path.splitext(old_file_key)[1]
        directory = os.path.dirname(old_file_key)
        new_file_key = f"{directory}/{ad_name}{file_extension}"
        new_file_url = await self.copy_object(old_file_key, new_file_key)

        return new_file_key, new_file_url
