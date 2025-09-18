from io import BytesIO
from typing import Annotated
from fastapi import Depends, UploadFile
from structlog import get_logger
from utils.dependencies import get_fal_client
from utils.exceptions import BadRequestError
from utils.fal_client import FalAIClient
from plugins.core.config.service import ConfigService, get_config_service
from .models import TranscribeResponse

logger = get_logger(__name__)


class TranscribeService:
    def __init__(
        self,
        config: Annotated[ConfigService, Depends(get_config_service)],
        fal_client: Annotated[FalAIClient, Depends(get_fal_client)],
    ):
        self.config = config
        self.fal = fal_client

    async def transcribe_audio(
        self, file: UploadFile, duration: float
    ) -> TranscribeResponse:
        min_duration = await self.config.get_or_create(
            "utilities/transcribe.min_duration_seconds",
            5,
            "Min audio duration for transcription.",
        )
        max_duration = await self.config.get_or_create(
            "utilities/transcribe.max_duration_seconds",
            600,
            "Max audio duration for transcription.",
        )
        model_name = await self.config.get_or_create(
            "utilities/transcribe.model_name",
            "fal-ai/wizper",
            "Fal.ai model for transcription (e.g., fal-ai/wizper).",
        )
        blocked_texts = await self.config.get_or_create(
            "utilities/transcribe.blocked_texts",
            ["DimaTorzok", "Субтитры делал", "Субтитры сделал", "Продолжение следует"],
            "List of phrases to block from transcription results.",
        )

        if not min_duration <= duration <= max_duration:
            logger.warning("Audio duration out of bounds", duration=duration)
            raise BadRequestError(
                f"Audio duration must be between {min_duration} and {max_duration} seconds."
            )

        audio_bytes = BytesIO(await file.read())

        transcription = await self.fal.transcribe_audio(
            model_name, audio_bytes, file.filename or "audio.ogg"
        )

        if any(text.lower() in transcription.lower() for text in blocked_texts):
            logger.info(
                "Transcription contains blocked text, returning empty.",
                transcription=transcription,
            )
            transcription = ""

        return TranscribeResponse(transcription=transcription, duration=duration)


def get_transcribe_service(
    service: Annotated[TranscribeService, Depends(TranscribeService)],
) -> TranscribeService:
    return service
