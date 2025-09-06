from typing import Annotated

from fastapi import Depends
from plugins.core.config.service import ConfigService, get_config_service
from structlog import get_logger
from plugins.neuro.ideogram.fal_models import IdeogramV3Input, RenderingSpeed
from utils.dependencies import get_fal_client
from utils.fal_client import FalAIClient

from .models import IdeogramDB, IdeogramResponse
from .repository import IdeogramRepository, get_ideogram_repository

logger = get_logger(__name__)


class IdeogramService:
    def __init__(
        self,
        fal_client: Annotated[FalAIClient, Depends(get_fal_client)],
        repository: Annotated[IdeogramRepository, Depends(get_ideogram_repository)],
        config: Annotated[ConfigService, Depends(get_config_service)],
    ):
        self.fal = fal_client
        self.repo = repository
        self.config = config

    async def generate(
        self,
        prompt: str,
        user_id: int,
        chat_id: int,
        negative_prompt: str | None = None,
    ) -> IdeogramResponse:
        model_name = await self.config.get_or_create(
            "neuro/ideogram.model", "fal-ai/ideogram/v3", "Fal.ai model for Ideogram."
        )
        default_neg_prompt = await self.config.get_or_create(
            "neuro/ideogram.default_negative_prompt",
            "ugly, deformed, noisy, blurry, distorted, out of focus, bad anatomy, extra limbs",
            "Default negative prompt for Ideogram.",
        )
        rendering_speed_str = await self.config.get_or_create(
            "neuro/ideogram.rendering_speed",
            "TURBO",
            "Rendering speed: TURBO, BALANCED, or QUALITY.",
        )
        rendering_speed = RenderingSpeed(rendering_speed_str.upper())

        final_negative_prompt = negative_prompt or default_neg_prompt

        payload = IdeogramV3Input(
            prompt=prompt,
            negative_prompt=final_negative_prompt,
            rendering_speed=rendering_speed,
            num_images=4,
        )

        result = await self.fal.generate_image(model_name, payload)

        image_urls = [img.url for img in result.images]
        seed = result.seed

        db_entry = IdeogramDB(
            user_id=user_id,
            chat_id=chat_id,
            prompt=prompt,
            negative_prompt=final_negative_prompt,
            image_urls=image_urls,
            model_used=model_name,
            seed=seed,
        )
        await self.repo.save_generation(db_entry)

        return IdeogramResponse(image_urls=image_urls, seed=seed)


def get_ideogram_service(
    service: Annotated[IdeogramService, Depends(IdeogramService)],
) -> IdeogramService:
    return service
