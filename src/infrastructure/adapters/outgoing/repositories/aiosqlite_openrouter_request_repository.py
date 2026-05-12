import logging
import json
from datetime import datetime, timezone

from src.domain.entities import Request
from src.application.ports.openrouter_request_repository import (
    OpenRouterRequestRepository,
)
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteOpenRouterRequestRepository(OpenRouterRequestRepository):
    """SQLite adapter implementing OpenRouterRequestRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def create(self, request: Request) -> None:
        self.logger.debug(
            f"Creating OpenRouter request for group {request.telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO openrouter_requests
                    (telegram_group_id,
                     success, model_openrouter_id,
                     prompt_tokens_usage, completion_tokens_usage,
                     cost_estimate_usd,
                     request_payload, response_content,
                     processing_time_ms, error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.telegram_group_id,
                        int(request.success) if request.success is not None else None,
                        request.model_openrouter_id,
                        request.prompt_tokens_usage,
                        request.completion_tokens_usage,
                        request.cost_estimate_usd,
                        json.dumps(request.request_payload, ensure_ascii=False)
                        if request.request_payload is not None
                        else None,
                        json.dumps(request.response_content, ensure_ascii=False)
                        if request.response_content is not None
                        else None,
                        request.processing_time_ms,
                        request.error_message,
                        int(request.created_at.timestamp()),
                    ),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(f"Error creating OpenRouter request: {e}")
                # Not raising as these requests are only for analytics
