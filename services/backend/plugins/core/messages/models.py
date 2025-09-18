from pydantic import BaseModel, Field


class SentimentQueueJob(BaseModel):
    """Data model for a job sent to the sentiment analysis queue."""

    id: str = Field(alias="_id")
    text: str
