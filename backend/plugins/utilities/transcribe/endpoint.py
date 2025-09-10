from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, UploadFile
from .models import TranscribeResponse
from .service import TranscribeService, get_transcribe_service

router = APIRouter()


@router.post(
    "",
    response_model=TranscribeResponse,
    summary="Transcribe an audio file",
)
async def transcribe_endpoint(
    service: Annotated[TranscribeService, Depends(get_transcribe_service)],
    audio_file: UploadFile = File(..., alias="file"),
    duration: float = Form(...),
):
    """
    Accepts an audio file and its duration, transcribes it, and returns the text.
    The file should be sent with the key 'file'.
    """
    return await service.transcribe_audio(audio_file, duration)
