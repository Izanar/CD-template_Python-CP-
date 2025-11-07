from pydantic import BaseModel


class MessageSchema(BaseModel):
    """Schema for a response just with message."""

    message: str
