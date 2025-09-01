import asyncio

import httpx
import structlog
from utils.exceptions import ServiceError

logger = structlog.get_logger(__name__)


class FalAIError(ServiceError):
    """Custom exception for Fal.run API errors."""

    def __init__(
        self, detail: str = "Fal.run API interaction failed", status_code: int = 502
    ):
        super().__init__(detail, status_code=status_code)


class FalAIClient:
    """A centralized client for the Fal.run API."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Fal.run API key is required.")

        self._base_url = "https://queue.fal.run"
        self._headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(headers=self._headers, timeout=180.0)

    async def generate_image(self, model_id: str, payload: dict) -> str:
        """
        Submits an image generation job and polls for the result, correctly handling
        model IDs with subpaths (e.g., 'fal-ai/flux/dev').
        """
        log = logger.bind(model_id=model_id)
        log.info("Submitting image generation job to Fal.run")

        try:
            parts = model_id.split("/")
            if len(parts) > 2:
                base_model_id = f"{parts[0]}/{parts[1]}"
                log.debug(
                    "Model ID with subpath detected",
                    full_id=model_id,
                    base_id=base_model_id,
                )
            else:
                base_model_id = model_id

            submit_response = await self._client.post(
                f"{self._base_url}/{model_id}", json=payload
            )
            submit_response.raise_for_status()
            response_data = submit_response.json()
            request_id = response_data.get("request_id")

            if not request_id:
                raise FalAIError("Fal.run submission did not return a request_id.")

            status_url = (
                f"{self._base_url}/{base_model_id}/requests/{request_id}/status"
            )
            result_url = f"{self._base_url}/{base_model_id}/requests/{request_id}"

            for attempt in range(45):
                await asyncio.sleep(2)
                status_check = await self._client.get(status_url)
                status_check.raise_for_status()
                status_data = status_check.json()

                status = status_data.get("status")
                log.debug(
                    "Polling Fal.run job",
                    request_id=request_id,
                    status=status,
                    attempt=attempt + 1,
                )

                if status == "COMPLETED":
                    result_response = await self._client.get(result_url)
                    result_response.raise_for_status()
                    result_data = result_response.json()

                    image_url = result_data.get("images", [{}])[0].get("url")
                    if not image_url:
                        raise FalAIError(
                            "Completed job did not contain an image URL.", result_data
                        )

                    log.info("Successfully generated image with Fal.run")
                    return image_url

                if status in ["FAILED", "ERROR"]:
                    log.error(
                        "Fal.run job failed",
                        request_id=request_id,
                        status_data=status_data,
                    )
                    raise FalAIError(
                        f"Image generation job failed with status: {status}"
                    )

            raise FalAIError("Image generation job timed out after 90 seconds.")

        except httpx.HTTPStatusError as e:
            log.error(
                "HTTP error from Fal.run API",
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise FalAIError(
                f"Fal.run API returned an error: {e.response.status_code}"
            ) from e
        except Exception as e:
            log.exception("An unexpected error occurred in FalAIClient")
            raise ServiceError(
                "An unexpected error occurred while contacting Fal.run."
            ) from e
