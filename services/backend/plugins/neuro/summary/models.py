from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Theme(BaseModel):
    """A single discussion theme identified by the LLM."""

    messages_id: List[int] = Field(
        description="3-4 message IDs marking the start, middle, and end of the discussion."
    )
    name: str = Field(description="A short, descriptive name for the theme in Russian.")
    emoji: str = Field(description="A single emoji that represents the theme.")
    key_takeaways: List[str] = Field(
        description="2-4 key takeaways summarizing the theme's main points in Russian."
    )


class LLMSummaryResponse(BaseModel):
    """The expected JSON structure from the summarization LLM."""

    themes: List[Theme] = Field(
        description="A list of summarized themes from the chat log."
    )
    bot_opinions: List[str] = Field(
        description="2-3 highly ironic, cynical, or funny opinions about the chat activity in Russian."
    )


class SummaryRequest(BaseModel):
    """Request body for the summary generation endpoint."""

    chat_id: int
    chat_title: str
    date: str = Field(description="The date for the summary in YYYY-MM-DD format.")


class SummaryResponse(BaseModel):
    """Response body for a successful summary generation."""

    summary_id: str
    formatted_text: str
    message_count: int


class SummaryDB(BaseModel):
    """Schema for storing a summary document in MongoDB."""

    chat_id: int
    chat_title: str
    summary_date: datetime
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    themes: List[dict]
    bot_opinions: List[str]
    message_count: int
    model_used: str
