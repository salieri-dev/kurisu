from typing import Any, Dict, List, Protocol


class TextAnalysisModel(Protocol):
    """
    Defines the interface for a text analysis model.
    Any model used in the worker should conform to this protocol.
    """

    def predict(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyzes a batch of texts and returns a list of structured results,
        one for each input text.
        """
        ...
