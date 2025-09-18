from io import BytesIO
import fal_client.client
import structlog
import fal_client
from pydantic import BaseModel, ValidationError
from utils.exceptions import ServiceError
from utils.fal_models import FalImageGenerationOutput

logger = structlog.get_logger(__name__)


class FalAIError(ServiceError):
    """Custom exception for Fal.run API errors."""

    def __init__(
        self, detail: str = "Fal.run API interaction failed", status_code: int = 502
    ):
        super().__init__(detail, status_code=status_code)


class FalAIClient:
    """
    A centralized client for the Fal.run API, using the official fal-client library.
    """

    def __init__(self):
        logger.info("FalAIClient initialized using official fal-client library.")

    async def transcribe_audio(
        self, model_id: str, audio_bytes: BytesIO, filename: str, language: str = "ru"
    ) -> str:
        """
        Uploads an audio file in-memory, submits it for transcription,
        and awaits the result.
        """
        log = logger.bind(model_id=model_id, filename=filename, language=language)
        try:
            log.info("Uploading audio file to Fal.ai storage via client library")
            audio_url = await fal_client.upload_async(
                data=audio_bytes.getvalue(),
                content_type="application/octet-stream",
                file_name=filename,
            )
            log.info(
                "Audio uploaded, submitting transcription job", audio_url=audio_url
            )

            handler = await fal_client.submit_async(
                model_id,
                arguments={
                    "audio_url": audio_url,
                    "task": "transcribe",
                    "language": language,
                },
            )

            result = await handler.get()
            transcription = result.get("text", "")
            log.info(
                "Transcription job completed successfully",
                result_length=len(transcription),
            )
            return transcription

        except fal_client.client.FalClientError as e:
            log.error("Fal.run client error during transcription", error=str(e))
            raise FalAIError(f"Fal.run API error: {e}") from e
        except Exception as e:
            log.exception(
                "An unexpected error occurred in FalAIClient during transcription"
            )
            raise ServiceError(
                "An unexpected error occurred while contacting Fal.run."
            ) from e

    async def generate_image(
        self, model_id: str, payload: BaseModel
    ) -> FalImageGenerationOutput:
        """
        Submits an image generation job using the fal-client library
        and returns a structured response.
        """
        log = logger.bind(model_id=model_id)
        try:
            log.info("Submitting image generation job via client library")
            handler = await fal_client.submit_async(
                model_id, arguments=payload.model_dump(exclude_none=True)
            )

            result_data = await handler.get()
            log.info("Image generation job completed successfully")

            return FalImageGenerationOutput.model_validate(result_data)

        except ValidationError as e:
            log.error(
                "Failed to validate final output from Fal.run",
                error=str(e),
                data=result_data,
            )
            raise FalAIError(
                "Fal.run returned an invalid 'COMPLETED' response structure."
            ) from e
        # CORRECTED: Use the full path to the exception class
        except fal_client.client.FalClientError as e:
            log.error("Fal.run client error during image generation", error=str(e))
            raise FalAIError(f"Fal.run API error: {e}") from e
        except Exception as e:
            log.exception(
                "An unexpected error occurred in FalAIClient during image generation"
            )
            raise ServiceError(
                "An unexpected error occurred while contacting Fal.run."
            ) from e
