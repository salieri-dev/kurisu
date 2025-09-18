
from pydantic import Field, MongoDsn, RedisDsn
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

    mongodb_url: MongoDsn = Field(..., alias="MONGODB_URL")
    mongodb_database: str = Field(..., alias="MONGO_DATABASE")
    redis_url: RedisDsn = Field(..., alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    owner_id: int = Field(..., alias="OWNER_ID")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = AppConfig()
