"""
Pydantic models representing the generic data structures for the Fal.ai Queue API.
These models are reusable across any plugin that interacts with Fal.ai.
"""

from typing import List, Literal

from pydantic import BaseModel, HttpUrl


class FalFile(BaseModel):
    """Represents a file object in a Fal.ai response."""

    url: HttpUrl
    content_type: str | None = None
    file_name: str | None = None
    file_size: int | None = None


class FalImageGenerationOutput(BaseModel):
    """
    Represents a common successful output structure for Fal.ai image generation models.
    """

    images: List[FalFile]
    seed: int


class FalQueueStatus(BaseModel):
    """
    Represents the status response from polling the Fal.ai queue.
    It can be a partial response (while in progress) or include the full output
    when the status is 'COMPLETED'.
    """

    status: Literal["IN_QUEUE", "IN_PROGRESS", "COMPLETED", "FAILED", "ERROR"]
    request_id: str
    images: List[FalFile] | None = None
    seed: int | None = None
