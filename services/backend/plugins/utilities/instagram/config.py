from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InstagramSettings(BaseSettings):
    """
    Configuration specific to the Instagram plugin, loaded from environment variables.
    This model is now self-contained and loaded only when the plugin is initialized.
    """

    INSTAGRAM_HEADERS_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_HEADERS_JSON")
    INSTAGRAM_COOKIES_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_COOKIES_JSON")
    INSTAGRAM_PAYLOAD_JSON: dict[str, Any] = Field(..., alias="INSTAGRAM_PAYLOAD_JSON")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
