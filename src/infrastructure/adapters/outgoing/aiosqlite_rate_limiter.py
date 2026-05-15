import time
import logging
from datetime import timedelta

from src.domain.exceptions import InternalRateLimitError
from src.application.ports.rate_limiter import RateLimiter
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteRateLimiter(RateLimiter):
    def __init__(
        self, db: AiosqliteDatabase, cleanup_window_hours: int, logger: logging.Logger
    ):
        self._db = db
        self.logger = logger
        self.cleanup_window_seconds = cleanup_window_hours * 3600

    async def check(self, key: str, limit: int, window: timedelta) -> None:
        current_time = time.time()
        cutoff = current_time - window.total_seconds()

        async with self._db.get_connection() as conn:
            # Single atomic statement: the INSERT only happens if COUNT < limit.
            cursor = await conn.execute(
                """
                INSERT INTO rate_limit_entries (key, timestamp)
                SELECT ?, ?
                WHERE (
                    SELECT COUNT(*) FROM rate_limit_entries
                    WHERE key = ? AND timestamp >= ?
                ) < ?
                """,
                (key, current_time, key, cutoff, limit),
            )
            await conn.commit()
            allowed = cursor.rowcount == 1

        self.logger.info(
            f"Rate limit check: key={key}, limit={limit}, "
            f"window={window.total_seconds()}s, allowed={allowed}"
        )
        if not allowed:
            raise InternalRateLimitError(f"Rate limit exceeded for key={key}")

    async def cleanup_expired_entries(self) -> None:
        cutoff = time.time() - self.cleanup_window_seconds

        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM rate_limit_entries WHERE timestamp < ?",
                (cutoff,),
            )
            await conn.commit()

            deleted_count = cursor.rowcount or 0
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} expired rate limit entries")
