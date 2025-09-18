from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InstagramConfig(BaseSettings):
    headers_json: dict[str, Any] = Field(..., alias="INSTAGRAM_HEADERS_JSON")
    cookies_json: dict[str, Any] = Field(..., alias="INSTAGRAM_COOKIES_JSON")
    payload_json: dict[str, Any] = Field(..., alias="INSTAGRAM_PAYLOAD_JSON")
    proxy_enabled: bool = Field(default=False, alias="PROXY_ENABLED")
    proxy_host: str | None = Field(default=None, alias="PROXY_HOST")
    proxy_port: int | None = Field(default=None, alias="PROXY_PORT")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


instagram_settings = InstagramConfig()
