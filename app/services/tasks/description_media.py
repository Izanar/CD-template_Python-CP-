import os
from typing import List, Sequence
from uuid import UUID


class DescriptionMediaOnCreateService:
    def __init__(self, media_repo, s3_bucket):
        self.media_repo = media_repo
        self.s3_bucket = s3_bucket

    async def attach(self, task_id: int, task_uuid: UUID, temp_keys: Sequence[str]) -> List[str]:
        if not temp_keys:
            return []

        env = os.getenv("ENV", "dev")
        final_keys: List[str] = []

        for temp_key in temp_keys:
            if not temp_key:
                continue
            try:
                final_key, _ = await self.s3_bucket.promote_temp_key(
                    temp_key=temp_key,
                    env=env,
                    task_uuid=str(task_uuid),
                )
                final_keys.append(final_key)
            except Exception:
                continue

        if final_keys:
            await self.media_repo.add_designer_task_images(
                task_id=task_id,
                file_keys=final_keys,
                s3_bucket=self.s3_bucket,
                is_description=True,
            )

        return final_keys
