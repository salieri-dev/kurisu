from pydantic import BaseModel, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotCredentials(BaseModel):
    name: str
    app_id: int
    api_hash: str
    bot_token: str


class Config(BaseSettings):
    bot_name: str = Field(..., alias="BOT_NAME")
    api_id: int = Field(..., alias="API_ID")
    api_hash: str = Field(..., alias="API_HASH")
    bot_token: str = Field(..., alias="BOT_TOKEN")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    api_key: str | None = Field(default=None, alias="API_KEY")

    redis_url: RedisDsn = Field(..., alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def bot(self) -> BotCredentials:
        return BotCredentials(
            name=self.bot_name,
            app_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token,
        )


credentials = Config()
