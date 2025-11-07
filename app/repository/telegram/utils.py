from __future__ import annotations

import os

from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyers.tasks.designer_tasks import DesignerTaskResponseSchema
from app.services.telegram import TelegramService

ENV_TO_SUBDOMAIN: dict[str, str] = {
    "dev": "develop",
    "stage": "stage",
    "main": "main",
}

ENV: str = os.getenv("ENV", "main").lower()
SUBDOMAIN: str = ENV_TO_SUBDOMAIN.get(ENV, "main")
BASE_URL: str = f"https://{SUBDOMAIN}.dlm8pjcdi1p9s.amplifyapp.com"
TASK_URL_TEMPLATE: str = f"{BASE_URL}/designers-tasks?task_id={{task_id}}"


async def notify_creator_task_ready(
    db_repo: DatabaseRepository,
    telegram_service: TelegramService,
    task: DesignerTaskResponseSchema,
) -> None:
    creator_chat_id = await db_repo.telegram.get_chat_id_by_user_id(task.created_by.id)
    if not creator_chat_id:
        return

    text = build_task_ready_message(task)

    await telegram_service.send_message(creator_chat_id, text)


def build_task_ready_message(task: DesignerTaskResponseSchema) -> str:
    task_url = TASK_URL_TEMPLATE.format(task_id=task.id)

    text = f"📝 Task {task.title} is ready for your review.\n\n{task_url}"

    return text
