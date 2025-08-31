# backend/config.py (Revised)

from typing import Any

from pydantic import Field, HttpUrl, MongoDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Application configuration settings loaded from environment variables.
    Provides validation and type casting for all settings.
    """

    service_name: str = Field(default="backend", alias="SERVICE_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    json_logs: bool = Field(default=False, alias="JSON_LOGS")
    api_key: str = Field(..., alias="API_KEY")

    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_base_url: HttpUrl = Field(..., alias="LLM_BASE_URL")
    llm_http_referer: str = Field(
        default="http://salieri.dev", alias="LLM_HTTP_REFERER"
    )
    llm_x_title: str = Field(default="not_salieri_bot", alias="LLM_X_TITLE")
    fal_api_key: str = Field(..., alias="FAL_API_KEY")
    instagram_headers_json: dict[str, Any] = Field(..., alias="INSTAGRAM_HEADERS_JSON")
    instagram_cookies_json: dict[str, Any] = Field(..., alias="INSTAGRAM_COOKIES_JSON")
    instagram_payload_json: dict[str, Any] = Field(..., alias="INSTAGRAM_PAYLOAD_JSON")

    proxy_enabled: bool = Field(default=False, alias="PROXY_ENABLED")
    proxy_host: str | None = Field(default=None, alias="PROXY_HOST")
    proxy_port: int | None = Field(default=None, alias="PROXY_PORT")

    mongodb_url: MongoDsn = Field(..., alias="MONGODB_URL")
    mongodb_database: str = Field(..., alias="MONGO_DATABASE")
    redis_url: RedisDsn = Field(..., alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = AppConfig()
