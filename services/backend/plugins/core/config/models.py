from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConfigItem(BaseModel):
    """Represents a configuration item stored in the database."""

    key: str = Field(
        ...,
        description="Unique key for the config, e.g., 'neuro/threads.system_prompt'",
    )
    value: Any = Field(
        ..., description="The configuration value. Can be any JSON-serializable type."
    )
    description: str | None = Field(
        None,
        description="Explanation of what this config does and its expected type/values.",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SetConfigRequest(BaseModel):
    """Request model for creating or updating a configuration item."""

    key: str
    value: Any
    description: str | None = None


class ConfigGetResponse(BaseModel):
    """Response model for a configuration item."""

    key: str
    value: Any
    description: str | None
    updated_at: datetime
