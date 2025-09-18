import base64
import random
from typing import Annotated, Literal

from fastapi import Depends
from plugins.core.config.service import ConfigService, get_config_service
from structlog import get_logger
from structlog.contextvars import bind_contextvars
from utils.asset_service import AssetService, get_asset_service
from utils.dependencies import get_llm_client
from utils.exceptions import BadRequestError, LLMError, ServiceError
from utils.llm_client import LLMClient

from .image_generator import DvachGenerator, FourChanGenerator
from .models import LLMStoryResponse, ThreadDB, ThreadResponse
from .prompts import BUGURT_SYSTEM_PROMPT, GREENTEXT_SYSTEM_PROMPT
from .repository import ThreadsRepository, get_threads_repository

logger = get_logger(__name__)

GENERATORS = {"bugurt": DvachGenerator, "greentext": FourChanGenerator}
PROMPTS = {"bugurt": BUGURT_SYSTEM_PROMPT, "greentext": GREENTEXT_SYSTEM_PROMPT}
ThreadType = Literal["bugurt", "greentext"]


class ThreadsService:
    def __init__(
        self,
        llm_client: Annotated[LLMClient, Depends(get_llm_client)],
        config_service: Annotated[ConfigService, Depends(get_config_service)],
        repository: Annotated[ThreadsRepository, Depends(get_threads_repository)],
        asset_service: Annotated[AssetService, Depends(get_asset_service)],
    ):
        self.llm_client = llm_client
        self.config_service = config_service
        self.repository = repository
        self.asset_service = asset_service

    async def generate_thread(
        self,
        thread_type: ThreadType,
        topic: str,
        user_id: int,
        chat_id: int,
    ) -> ThreadResponse:
        bind_contextvars(thread_type=thread_type, topic=topic)

        model_name = await self.config_service.get_or_create(
            f"neuro/threads.{thread_type}.model",
            "anthropic/claude-3.5-sonnet",
            f"LLM for {thread_type}.",
        )
        system_prompt_template = await self.config_service.get_or_create(
            f"neuro/threads.{thread_type}.system_prompt",
            PROMPTS[thread_type],
            f"Prompt for {thread_type}.",
        )
        if not isinstance(model_name, str) or not isinstance(
            system_prompt_template, str
        ):
            raise ServiceError("Invalid configuration for threads plugin.")

        post_id = str(random.randint(10000000, 99999999))
        comment_ids = [str(int(post_id) + i + 1) for i in range(4)]
        comment_ids_str = ", ".join(comment_ids)
        system_prompt = system_prompt_template.format(
            post_id=post_id, comment_ids=comment_ids_str
        )
        user_prompt = f"The user's theme is: '{topic}'."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            llm_response = await self.llm_client.structured_chat_completion(
                messages=messages,
                model=model_name,
                response_model=LLMStoryResponse,
            )

        except (LLMError, BadRequestError) as e:
            raise e
        except Exception as e:
            logger.exception("An unexpected error occurred during LLM generation.")
            raise ServiceError(
                "An unexpected error occurred during LLM generation."
            ) from e

        Generator = GENERATORS[thread_type]
        image_generator = Generator(asset_service=self.asset_service)
        image_bytes = image_generator.generate(llm_response, post_id)

        thread_data = ThreadDB(
            user_id=user_id,
            chat_id=chat_id,
            command=thread_type,
            topic=topic,
            story=llm_response.story,
            comments=llm_response.comments,
            model_used=model_name,
        )
        await self.repository.save_thread(thread_data)

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return ThreadResponse(image_base64=image_base64, story=llm_response.story)


THREADS_SERVICE_DEPENDENCY = Depends(ThreadsService)


def get_threads_service(
    service: ThreadsService = THREADS_SERVICE_DEPENDENCY,
) -> ThreadsService:
    return service
