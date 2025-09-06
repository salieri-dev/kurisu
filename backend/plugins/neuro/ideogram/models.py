from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, HttpUrl


class IdeogramRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    negative_prompt: str | None = None
    # Add other parameters like style if you wish to support them


class IdeogramResponse(BaseModel):
    image_urls: List[HttpUrl]
    seed: int | None = None


class IdeogramDB(BaseModel):
    user_id: int
    chat_id: int
    prompt: str
    negative_prompt: str | None
    image_urls: List[HttpUrl]
    model_used: str
    seed: int | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
