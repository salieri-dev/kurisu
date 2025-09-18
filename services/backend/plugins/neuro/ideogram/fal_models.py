"""Pydantic models representing the INPUT schema for the fal-ai/ideogram/v3 API."""

from enum import Enum
from pydantic import BaseModel, Field


class RenderingSpeed(str, Enum):
    TURBO = "TURBO"
    BALANCED = "BALANCED"
    QUALITY = "QUALITY"


class ImageSizePreset(str, Enum):
    SQUARE_HD = "square_hd"
    SQUARE = "square"
    PORTRAIT_4_3 = "portrait_4_3"
    PORTRAIT_16_9 = "portrait_16_9"
    LANDSCAPE_4_3 = "landscape_4_3"
    LANDSCAPE_16_9 = "landscape_16_9"


class IdeogramV3Input(BaseModel):
    """Payload for submitting a job to fal-ai/ideogram/v3."""

    prompt: str
    rendering_speed: RenderingSpeed = RenderingSpeed.BALANCED
    num_images: int = Field(default=4, ge=1, le=8)
    image_size: ImageSizePreset = ImageSizePreset.SQUARE_HD
    negative_prompt: str | None = None
    seed: int | None = None
    expand_prompt: bool = True
