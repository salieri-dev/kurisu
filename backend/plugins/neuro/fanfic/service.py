# backend/plugins/neuro/fanfic/service.py
from typing import Annotated

from fastapi import Depends
from plugins.core.config.service import ConfigService, get_config_service
from pydantic import ValidationError
from structlog import get_logger
from utils.dependencies import get_fal_client, get_llm_client
from utils.exceptions import LLMError
from utils.fal_client import FalAIClient
from utils.llm_client import LLMClient

from .models import FanficDB, FanficResponse, LLMFanficResponse
from .prompts import DEFAULT_SYSTEM_PROMPT
from .repository import FanficRepository, get_fanfic_repository

logger = get_logger(__name__)


class FanficService:
    def __init__(
        self,
        llm_client: Annotated[LLMClient, Depends(get_llm_client)],
        fal_client: Annotated[FalAIClient, Depends(get_fal_client)],
        repository: Annotated[FanficRepository, Depends(get_fanfic_repository)],
        config: Annotated[ConfigService, Depends(get_config_service)],
    ):
        self.llm = llm_client
        self.fal = fal_client
        self.repo = repository
        self.config = config

    async def generate_fanfic(
        self, topic: str, user_id: int, chat_id: int
    ) -> FanficResponse:
        # 1. Get dynamic configuration
        model = await self.config.get_or_create(
            "neuro/fanfic.model", "anthropic/claude-3.5-sonnet", "LLM for fanfics."
        )
        image_model = await self.config.get_or_create(
            "neuro/fanfic.image_model", "fal-ai/flux/dev", "Fal.run model for posters."
        )
        system_prompt = await self.config.get_or_create(
            "neuro/fanfic.system_prompt",
            DEFAULT_SYSTEM_PROMPT,
            "System prompt for fanfic generation.",
        )

        # 2. Generate story and image prompt with LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The user's topic is: '{topic}'."},
        ]
        try:
            json_string = await self.llm.chat_completion(
                messages, model, response_format={"type": "json_object"}
            )
            llm_data = LLMFanficResponse.model_validate_json(json_string)
        except (ValidationError, LLMError) as e:
            logger.error(
                "LLM failed to produce valid fanfic response",
                error=str(e),
                response=json_string,
            )
            raise LLMError(
                "The language model returned a malformed response. Please try again."
            ) from e

        # 3. Generate image with Fal.run
        image_payload = {
            "prompt": llm_data.image_prompt,
            "image_size": "landscape_4_3",
            "num_images": 1,
        }
        image_url = await self.fal.generate_image(image_model, image_payload)

        # 4. Save to database
        db_entry = FanficDB(
            user_id=user_id,
            chat_id=chat_id,
            topic=topic,
            title=llm_data.title,
            content=llm_data.content,
            image_prompt=llm_data.image_prompt,
            image_url=image_url,
            model_used=model,
        )
        await self.repo.save_fanfic(db_entry)

        # 5. Return response for API
        return FanficResponse(
            title=llm_data.title, content=llm_data.content, image_url=image_url
        )


def get_fanfic_service(
    service: Annotated[FanficService, Depends(FanficService)],
) -> FanficService:
    return service
