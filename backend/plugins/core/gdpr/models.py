"""Pydantic models for GDPR operations."""

from pydantic import BaseModel, ConfigDict


class GDPRDeleteRequest(BaseModel):
    """Request model for GDPR data deletion."""

    user_id: int

    model_config = ConfigDict(json_schema_extra={"examples": [{"user_id": 283902044}]})


class GDPRDeleteResponse(BaseModel):
    """Response model for GDPR data deletion operations."""

    success: bool
    deleted_count: int
    error: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"success": True, "deleted_count": 42, "error": None}]
        }
    )
