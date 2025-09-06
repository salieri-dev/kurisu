from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ChatProfileUpdate(BaseModel):
    """A single chat profile update sent from the bot."""

    chat_id: int
    status: str
    chat_info: Dict[str, Any]


class UpdateChatsRequest(BaseModel):
    """The request body for the bulk update endpoint."""

    updates: List[ChatProfileUpdate]


class ChatIDListResponse(BaseModel):
    chat_ids: List[int]


class StatusHistoryEntry(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatProfileDB(BaseModel):
    chat_id: int = Field(..., unique=True)
    chat_info: Dict[str, Any]
    current_status: str
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    status_history: List[StatusHistoryEntry] = []
