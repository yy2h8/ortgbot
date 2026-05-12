class OpenRouterRateLimitError(Exception):
    """Raised when OpenRouter returns a 429 rate limit error"""

    pass


class InternalRateLimitError(Exception):
    """Raised when internal rate limit is exceeded."""

    pass
