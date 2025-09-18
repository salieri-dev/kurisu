from pydantic import Field, HttpUrl, MongoDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    """
    Configuration for the message processing worker.
    """

    service_name: str = Field(default="worker", alias="SERVICE_NAME")
    json_logs: bool = Field(default=False, alias="JSON_LOGS")
    api_key: str | None = Field(default=None, alias="API_KEY")

    redis_url: RedisDsn = Field(..., alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    mongodb_url: MongoDsn = Field(..., alias="MONGODB_URL")
    mongodb_database: str = Field(..., alias="MONGO_DATABASE")
    backend_url: HttpUrl = Field(..., alias="BACKEND_URL")

    batch_size: int = Field(default=10, alias="BATCH_SIZE", ge=1)
    batch_timeout_seconds: int = Field(default=5, alias="BATCH_TIMEOUT", ge=1)

    max_retry_attempts: int = Field(default=3, alias="MAX_RETRY_ATTEMPTS", ge=0)
    base_retry_delay_seconds: float = Field(default=1.0, alias="BASE_RETRY_DELAY", ge=0)
    max_retry_delay_seconds: float = Field(default=60.0, alias="MAX_RETRY_DELAY", ge=0)

    connect_retry_attempts: int = Field(
        default=10, alias="CONNECT_RETRY_ATTEMPTS", ge=1
    )
    connect_retry_delay_seconds: float = Field(
        default=2.0, alias="CONNECT_RETRY_DELAY", ge=1
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = WorkerConfig()
