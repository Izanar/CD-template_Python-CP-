from sqlalchemy import select, update

from app.models import MediaBuyer, User
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.assistant.base import AssistantBaseRepository
from app.repository.media_buyers.assistant.utils import validate_assistant_assignment
from app.schemas.media_buyer import SetAssistantSchema
from app.schemas.user import UserResponseSchema


class AssistantRepository(AssistantBaseRepository, DatabaseEngineRepository):
    async def set_assistant(self, assistant_data: SetAssistantSchema) -> UserResponseSchema:
        async with self.session_maker() as db:
            await validate_assistant_assignment(db, assistant_data.teacher_id, assistant_data.assistant_id)

            await db.execute(
                update(MediaBuyer)
                .where(MediaBuyer.id == assistant_data.assistant_id)
                .values(assistant_reference_id=assistant_data.teacher_id)
            )
            await db.commit()

            return await db.scalar(select(User).where(User.id == assistant_data.teacher_id))
