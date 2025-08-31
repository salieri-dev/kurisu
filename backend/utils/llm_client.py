# backend/utils/llm_client.py (Revised chat_completion)

import structlog
from openai import APIConnectionError, APIStatusError, AsyncOpenAI
from utils.exceptions import LLMError, ServiceError

logger = structlog.get_logger(__name__)


class LLMClient:
    """A centralized, generic client for OpenAI-compatible LLM APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        http_referer: str,
        x_title: str,
    ):
        """Initializes the asynchronous LLM client."""
        if not api_key or not base_url:
            raise ValueError("LLM API key and Base URL are required.")

        default_headers = {
            "HTTP-Referer": http_referer,
            "X-Title": x_title,
        }

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=180.0,
            default_headers=default_headers,
        )

    async def chat_completion(
        self, messages: list[dict[str, str]], model: str, **kwargs
    ) -> str:
        """
        Performs a chat completion request to the configured LLM API.

        Args:
            messages: A list of message dictionaries.
            model: The model to use for the completion.
            **kwargs: Additional arguments to pass to the OpenAI client's create method
                      (e.g., response_format, temperature).

        Returns:
            The content of the assistant's response message as a string.
        """
        log = logger.bind(model=model, api_provider="openai_compatible")
        log.info(
            "Requesting chat completion", headers=self._client.default_headers, **kwargs
        )

        try:
            response = await self._client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )

            if not response.choices or not response.choices[0].message.content:
                log.error(
                    "Invalid response structure from LLM API", response_data=response
                )
                raise LLMError("Received an invalid response structure from the LLM.")

            content = response.choices[0].message.content
            log.info(
                "Successfully received chat completion",
                usage=response.usage,
            )
            return content

        except APIStatusError as e:
            log.error(
                "LLM API returned an error status",
                status_code=e.status_code,
                response_body=e.response.text,
            )
            raise LLMError(
                f"LLM API returned an error: {e.status_code} - {e.response.text}",
                status_code=e.status_code,
            ) from e
        except APIConnectionError as e:
            log.error("Network error during LLM API request", error=str(e))
            raise ServiceError(
                f"A network error occurred while contacting the LLM: {e}"
            ) from e
        except Exception as e:
            log.exception("An unexpected error occurred in LLMClient")
            raise ServiceError(
                "An unexpected error occurred while contacting the LLM."
            ) from e
