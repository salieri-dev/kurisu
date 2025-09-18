from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class DashboardConfig(BaseSettings):
    service_name: str = Field(default="dashboard", alias="SERVICE_NAME")
    backend_url: HttpUrl = Field(..., alias="BACKEND_URL")
    api_key: str = Field(..., alias="API_KEY")
    json_logs: bool = Field(default=False, alias="JSON_LOGS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = DashboardConfig()
