from typing import Dict, List
import torch
from transformers import pipeline
import structlog

logger = structlog.get_logger(__name__)


class SentimentModel:
    """Encapsulates the sentiment analysis model and its logic."""

    _ID_TO_NAME = {
        0: "negative",
        1: "neutral",
        2: "positive",
        3: "skip",
        4: "speech_act",
    }

    def __init__(self, model_name: str, device: torch.device):
        logger.info("Loading sentiment model...", model=model_name, device=str(device))
        logger.info("test")
        self.pipeline = pipeline(
            task="text-classification", model=model_name, device=device, top_k=None
        )
        logger.info("Sentiment model loaded successfully.")

    def predict(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        Predicts sentiment for a batch of texts using a model that outputs LABEL_X format.
        Returns:
            A list of dictionaries, where each dictionary contains label-score pairs.
            e.g., [{'negative': 0.9, 'neutral': 0.05, 'positive': 0.01, 'skip': 0.02, 'speech_act': 0.02}, ...]
        """
        if not texts:
            return []
        with torch.no_grad():
            raw_results = self.pipeline(texts, truncation=True, max_length=512)
        processed_results = []
        for batch_result in raw_results:
            score_map = {}
            for item in batch_result:
                try:
                    label_id = int(item["label"].split("_")[-1])
                    label_name = self._ID_TO_NAME[label_id]
                    score_map[label_name] = item["score"]
                except (ValueError, KeyError, IndexError) as e:
                    logger.warning(
                        "Could not parse model output label",
                        label=item.get("label"),
                        error=str(e),
                    )
            processed_results.append(score_map)
        return processed_results
