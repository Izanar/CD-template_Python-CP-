from pydantic import BaseModel


class TelegramChatIDResponse(BaseModel):
    chat_id: int | None
