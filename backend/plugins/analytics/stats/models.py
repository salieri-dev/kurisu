from typing import List, Any
from pydantic import BaseModel, Field


class CountByGroup(BaseModel):
    group: Any = Field(
        ..., description="The value being grouped by (e.g., chat type, media type)."
    )
    count: int = Field(..., description="The number of items in this group.")


class TopChatItem(BaseModel):
    chat_id: int
    title: str | None
    type: str | None
    message_count: int


class TopUserItem(BaseModel):
    user_id: int
    display_name: str
    message_count: int


class FullStatsResponse(BaseModel):
    total_messages: int
    total_unique_users: int
    monthly_active_users: int
    monthly_command_users: int
    most_active_hour_moscow: int | None
    least_active_hour_moscow: int | None
    messages_by_chat_type: List[CountByGroup]
    messages_by_media_type: List[CountByGroup]
    top_10_chats: List[TopChatItem]
    top_10_monthly_active_users: List[TopUserItem]
