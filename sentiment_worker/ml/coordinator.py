# sentiment_worker/ml/coordinator.py

from typing import Dict, List, Any
import torch
import structlog

from .sentiment import SentimentModel
from .topics import SensitiveTopicsModel

logger = structlog.get_logger(__name__)


class ModelCoordinator:
    """
    Loads all ML models and orchestrates the analysis pipeline.
    """

    def __init__(
        self, sentiment_model_name: str, topics_model_name: str, device_str: str
    ):
        self.device = torch.device(device_str if torch.cuda.is_available() else "cpu")
        logger.info(f"ModelCoordinator initializing on device: {self.device}")

        self.sentiment_model = SentimentModel(sentiment_model_name, self.device)
        self.topics_model = SensitiveTopicsModel(topics_model_name, self.device)

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Runs a batch of texts through the full analysis pipeline.

        Returns:
            A list of combined analysis results for each text.
            e.g., [{'sentiment': {...}, 'sensitive_topics': {...}}, ...]
        """
        if not texts:
            return []

        sentiment_results = self.sentiment_model.predict(texts)
        topics_results = self.topics_model.predict(texts)

        combined_results = []
        for sentiment, topics in zip(sentiment_results, topics_results):
            combined_results.append(
                {"sentiment": sentiment, "sensitive_topics": topics}
            )

        return combined_results
