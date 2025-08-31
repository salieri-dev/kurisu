"""Pydantic models for GDPR operations."""

from typing import Optional

from pydantic import BaseModel


class GDPRDeleteRequest(BaseModel):
    """Request model for GDPR data deletion."""

    user_id: int

    class Config:
        json_schema_extra = {"example": {"user_id": 283902044}}


class GDPRDeleteResponse(BaseModel):
    """Response model for GDPR data deletion operations."""

    success: bool
    deleted_count: int
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"success": True, "deleted_count": 42, "error": None}
        }
