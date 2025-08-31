from typing import Optional


class APIError(Exception):
    """
    Custom exception raised for errors from the backend API.

    This exception consolidates information from the HTTP response,
    making it easier to handle and report API errors consistently.
    """

    def __init__(
        self, detail: str, status_code: int, correlation_id: Optional[str] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.correlation_id = correlation_id
        message = f"API Error: [Status={status_code}] [CorrelationID={correlation_id}] - {detail}"
        super().__init__(message)

    def __str__(self):
        return f"APIError(status_code={self.status_code}, detail='{self.detail}', correlation_id='{self.correlation_id}')"
