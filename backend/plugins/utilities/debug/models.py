# backend/plugins/utilities/debug/models.py
from typing import Literal

from pydantic import BaseModel, Field

LogLevel = Literal["info", "warning", "error", "exception"]


class DebugRequest(BaseModel):
    """Defines the parameters for generating a debug event."""

    log_level: LogLevel = Field(
        default="info", description="The level of the log message to generate."
    )
    log_message: str = Field(
        default="This is a test log message.",
        description="The content of the log message.",
    )
    http_status_code: int = Field(
        default=200,
        description="The HTTP status code to return. Non-200 codes will raise an exception.",
    )
    delay_seconds: float = Field(
        default=0,
        ge=0,
        le=30,
        description="An artificial delay to add to the request to simulate latency.",
    )
    create_spans: bool = Field(
        default=False,
        description="If true, creates a custom trace with multiple child spans.",
    )
