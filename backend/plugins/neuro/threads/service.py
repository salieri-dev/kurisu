import base64
import random
from typing import Annotated, Literal

from fastapi import Depends
from plugins.core.config.service import ConfigService, get_config_service
from pydantic import ValidationError
from structlog import get_logger
from structlog.contextvars import bind_contextvars
from utils.dependencies import get_llm_client
from utils.exceptions import BadRequestError, LLMError, ServiceError
from utils.llm_client import LLMClient

from .image_generator import DvachGenerator, FourChanGenerator
from .models import LLMStoryResponse, ThreadDB, ThreadResponse
from .prompts import BUGURT_SYSTEM_PROMPT, GREENTEXT_SYSTEM_PROMPT
from .repository import ThreadsRepository, get_threads_repository

logger = get_logger(__name__)

GENERATORS = {
    "bugurt": DvachGenerator,
    "greentext": FourChanGenerator,
}

PROMPTS = {
    "bugurt": BUGURT_SYSTEM_PROMPT,
    "greentext": GREENTEXT_SYSTEM_PROMPT,
}

ThreadType = Literal["bugurt", "greentext"]


class ThreadsService:
    def __init__(
        self,
        llm_client: Annotated[LLMClient, Depends(get_llm_client)],
        config_service: Annotated[ConfigService, Depends(get_config_service)],
        repository: Annotated[ThreadsRepository, Depends(get_threads_repository)],
    ):
        self.llm_client = llm_client
        self.config_service = config_service
        self.repository = repository

    async def generate_thread(
        self,
        thread_type: ThreadType,
        topic: str,
        user_id: int,
        chat_id: int,
    ) -> ThreadResponse:
        bind_contextvars(thread_type=thread_type, topic=topic)

        # 1. Get configuration
        model_name = await self.config_service.get_or_create(
            f"neuro/threads.{thread_type}.model",
            default="anthropic/claude-3.5-sonnet",
            description=f"LLM model used for generating {thread_type} stories.",
        )
        system_prompt_template = await self.config_service.get_or_create(
            f"neuro/threads.{thread_type}.system_prompt",
            default=PROMPTS[thread_type],
            description=f"The system prompt for generating {thread_type} stories.",
        )

        if not isinstance(model_name, str) or not isinstance(
            system_prompt_template, str
        ):
            raise ServiceError("Invalid configuration found for threads plugin.")

        # --- NEW LOGIC: Generate and format IDs ---
        post_id = str(random.randint(10000000, 99999999))
        comment_ids = [str(int(post_id) + i + 1) for i in range(4)]
        comment_ids_str = ", ".join(comment_ids)

        system_prompt = system_prompt_template.format(
            post_id=post_id, comment_ids=comment_ids_str
        )
        user_prompt = f"The user's theme is: '{topic}'. The post ID is {post_id} and potential comment IDs are {comment_ids_str}."
        # --- END NEW LOGIC ---

        # 2. Call LLM for structured story and comments
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},  # Use the new user_prompt
        ]
        try:
            json_string_response = await self.llm_client.chat_completion(
                messages=messages,
                model=model_name,
                response_format={"type": "json_object"},
            )
            llm_response = LLMStoryResponse.model_validate_json(json_string_response)

        except ValidationError as e:
            logger.error(
                "LLM failed to produce valid JSON for Pydantic model",
                error=str(e),
                llm_response=json_string_response,
            )
            raise LLMError(
                "The language model returned a malformed response. Please try again."
            ) from e
        except (LLMError, BadRequestError) as e:
            raise e
        except Exception as e:
            logger.exception("An unexpected error occurred during LLM generation.")
            raise ServiceError(
                "An unexpected error occurred during LLM generation."
            ) from e

        # 3. Generate image from LLM response
        Generator = GENERATORS[thread_type]
        # Pass the post_id to the generator
        image_bytes = Generator().generate(llm_response, post_id)

        # 4. Save to database
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

        # 5. Return response for API
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return ThreadResponse(image_base64=image_base64, story=llm_response.story)


def get_threads_service(
    service: ThreadsService = Depends(ThreadsService),
) -> ThreadsService:
    return service
