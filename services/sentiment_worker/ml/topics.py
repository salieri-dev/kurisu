# sentiment_worker/ml/topics.py

import json
from pathlib import Path
from typing import Dict, List
import torch
import torch.nn.functional as F
from transformers import BertForSequenceClassification, BertTokenizer
import structlog

logger = structlog.get_logger(__name__)


class SensitiveTopicsModel:
    """Encapsulates the sensitive topics detection model and its logic."""

    def __init__(self, model_name: str, device: torch.device):
        logger.info(
            "Loading sensitive topics model...", model=model_name, device=str(device)
        )
        self.device = device
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(model_name).to(
            self.device
        )
        self.model.eval()

        topic_file = Path(__file__).parent.parent / "id2topic.json"
        with topic_file.open() as f:
            self.topic_map = json.load(f)

        logger.info("Sensitive topics model loaded successfully.")

    def predict(
        self, texts: List[str], threshold: float = 0.1
    ) -> List[Dict[str, float]]:
        """
        Predicts sensitive topics for a batch of texts.

        Returns:
            A list of dictionaries, where each key is a topic and value is its score,
            filtered by the threshold.
            e.g., [{'politics': 0.87, 'insults': 0.23}, {}, ...]
        """
        if not texts:
            return []

        with torch.no_grad():
            encoded = self.tokenizer.batch_encode_plus(
                texts,
                max_length=256,
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(self.device)

            outputs = self.model(**encoded)
            probabilities = F.softmax(outputs.logits, dim=-1).cpu().numpy()

        return [
            {
                self.topic_map[str(idx)]: float(prob)
                for idx, prob in enumerate(probs)
                if float(prob) >= threshold and self.topic_map[str(idx)] != "none"
            }
            for probs in probabilities
        ]
