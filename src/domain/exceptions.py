class OpenRouterRateLimitError(Exception):
    """Raised when OpenRouter returns a 429 rate limit error"""

    pass


class EmptyResponseError(Exception):
    """Raised when OpenRouter returns a 200 OK but with empty content after all retries."""

    pass


class InternalRateLimitError(Exception):
    """Raised when internal rate limit is exceeded."""

    pass
