from typing import Dict, List
import torch
from transformers import pipeline
import structlog

logger = structlog.get_logger(__name__)


class SentimentModel:
    """Encapsulates the sentiment analysis model and its logic."""

    def __init__(self, model_name: str, device: torch.device):
        logger.info("Loading sentiment model...", model=model_name, device=str(device))
        self.pipeline = pipeline(
            task="text-classification", model=model_name, device=device
        )
        logger.info("Sentiment model loaded successfully.")

    def predict(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        Predicts sentiment for a batch of texts.

        Returns:
            A list of dictionaries, where each dictionary contains label-score pairs.
            e.g., [{'positive': 0.98, 'neutral': 0.01, 'negative': 0.01}, ...]
        """
        if not texts:
            return []

        with torch.no_grad():
            results = self.pipeline(texts, top_k=None)

        return [
            {item["label"].lower(): item["score"] for item in batch_result}
            for batch_result in results
        ]
