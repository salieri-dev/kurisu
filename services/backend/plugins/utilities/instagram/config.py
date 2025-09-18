from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings


class InstagramSettings(BaseSettings):
    """Configuration specific to the Instagram plugin."""

    INSTAGRAM_HEADERS_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_HEADERS_JSON")
    INSTAGRAM_COOKIES_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_COOKIES_JSON")
    INSTAGRAM_PAYLOAD_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_PAYLOAD_JSON")

    class Config:
        extra = "ignore"
