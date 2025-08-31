from datetime import datetime

from pydantic import BaseModel, Field


# For API endpoint
class FanficRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300)


class FanficResponse(BaseModel):
    title: str
    content: str
    image_url: str


# For LLM structured output
class LLMFanficResponse(BaseModel):
    title: str = Field(description="The title of the fanfiction in Russian.")
    content: str = Field(
        description="The full text of the fanfiction in Russian, approximately 500-1000 words."
    )
    image_prompt: str = Field(
        description="A highly detailed, SFW image prompt in English to generate a poster for the story. Focus on character appearances, setting, and mood."
    )


# For Database
class FanficDB(BaseModel):
    user_id: int
    chat_id: int
    topic: str
    title: str
    content: str
    image_prompt: str
    image_url: str
    model_used: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
