"""
Provider-level error types for HTTP communication failures.

These are infrastructure-layer exceptions that provider adapters raise;
the application layer maps them to domain exceptions
(``ProviderUnavailableError``, ``BookingError``, etc.).
"""


class ProviderHTTPError(Exception):
    """Non-retryable HTTP error from a logistics provider."""

    def __init__(
        self,
        status_code: int,
        message: str = "",
        response_body: str | None = None,
    ):
        self.status_code: int = status_code
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


class ProviderTimeoutError(Exception):
    """Request to a logistics provider timed out after retries."""

    def __init__(self, message: str = "Provider request timed out"):
        super().__init__(message)


class ProviderAuthError(Exception):
    """Authentication with a logistics provider failed."""

    def __init__(self, message: str = "Provider authentication failed"):
        super().__init__(message)
