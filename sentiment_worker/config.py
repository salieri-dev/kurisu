from pydantic import Field, MongoDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    service_name: str = Field(default="sentiment-worker", alias="SERVICE_NAME")
    json_logs: bool = Field(default=False, alias="JSON_LOGS")

    redis_url: RedisDsn = Field(..., alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    mongodb_url: MongoDsn = Field(..., alias="MONGODB_URL")
    mongodb_database: str = Field(..., alias="MONGO_DATABASE")

    sentiment_model: str = Field(
        default="seara/rubert-tiny2-russian-sentiment", alias="SENTIMENT_MODEL"
    )
    sensitive_topics_model: str = Field(
        default="Skoltech/russian-sensitive-topics", alias="SENSITIVE_TOPICS_MODEL"
    )

    batch_size: int = Field(default=32, alias="SENTIMENT_BATCH_SIZE")
    model_device: str = Field(default="gpu", alias="SENTIMENT_MODEL_DEVICE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = WorkerConfig()
