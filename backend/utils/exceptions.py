class ServiceError(Exception):
    """Base exception for all service-layer errors."""

    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=404)


class BadRequestError(ServiceError):
    """Raised for invalid client requests (e.g., bad input)."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(detail, status_code=400)


class LLMError(ServiceError):
    """Raised for errors related to Large Language Model interactions."""

    def __init__(self, detail: str = "LLM interaction failed", status_code: int = 502):
        super().__init__(detail, status_code=status_code)
