from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class RateLimiter(ABC):
    """Port for rate limiting operations"""

    @abstractmethod
    async def check(self, key: str, limit: int, window: timedelta) -> None:
        """Check if an action is within rate limit.

        Args:
            key: Unique identifier (e.g., "group:123456", "user:789", "api:global")
            limit: Maximum number of actions allowed in window
            window: Time window as timedelta

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        raise NotImplementedError("Method 'check' not implemented")

    @abstractmethod
    async def cleanup_expired_entries(self) -> None:
        """Clean up expired rate limit entries."""
        raise NotImplementedError("Method 'cleanup_expired_entries' not implemented")
