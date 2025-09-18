from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response model for a successful transcription."""

    transcription: str = Field(description="The transcribed text from the audio.")
    duration: float = Field(description="The duration of the audio in seconds.")
