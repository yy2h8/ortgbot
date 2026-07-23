import logging
import time
from datetime import timedelta

from src.domain.entities import Request
from src.domain.dto import OpenRouterResponse, Prompt, ConversationPrompt
from src.domain.exceptions import OpenRouterRateLimitError
from src.application.ports.openrouter_client import OpenRouterClient
from src.application.ports.openrouter_request_repository import (
    OpenRouterRequestRepository,
)
from src.application.ports.rate_limiter import RateLimiter


class AIService:
    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        request_repo: OpenRouterRequestRepository,
        rate_limiter: RateLimiter,
        logger: logging.Logger,
        global_api_calls_per_day: int,
    ):
        self.openrouter_client = openrouter_client
        self.request_repo = request_repo
        self.rate_limiter = rate_limiter
        self.logger = logger
        self.global_api_calls_per_day = global_api_calls_per_day

    async def request(
        self,
        model_id: str,
        group_id: int,
        prompt: Prompt,
    ) -> OpenRouterResponse:
        """Make a single AI request with request tracking."""
        await self.rate_limiter.check(
            key="global_api_calls",
            limit=self.global_api_calls_per_day,
            window=timedelta(days=1),
        )

        start_time = time.time()
        try:
            response = await self.openrouter_client.request(
                prompt=prompt,
                model=model_id,
            )
            await self.request_repo.create(
                Request.create(
                    telegram_group_id=group_id,
                    success=True,
                    model_openrouter_id=model_id,
                    prompt_tokens_usage=response.prompt_tokens,
                    completion_tokens_usage=response.completion_tokens,
                    cost_estimate_usd=response.cost,
                    request_payload=response.request_payload,
                    response_content=response.raw_response,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            )
            return response
        except OpenRouterRateLimitError:
            raise
        except Exception as e:
            await self.request_repo.create(
                Request.create(
                    telegram_group_id=group_id,
                    success=False,
                    model_openrouter_id=model_id,
                    request_payload={
                        "system_prompt": prompt.system,
                        "user_prompt": prompt.user,
                        "max_tokens": prompt.max_tokens,
                        "temperature": prompt.temperature,
                    },
                    error_message=str(e),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            )
            raise

    async def request_with_paid_fallback(
        self,
        free_model_id: str,
        paid_model_id: str,
        group_id: int,
        prompt: Prompt,
    ) -> OpenRouterResponse:
        """Make AI request with free/paid model fallback."""
        self.logger.info(
            f"Making AI request with free model {free_model_id}, fallback: {paid_model_id}"
        )

        try:
            response = await self.request(
                model_id=free_model_id,
                group_id=group_id,
                prompt=prompt,
            )
            return response
        except OpenRouterRateLimitError as e:
            self.logger.warning(f"Rate limited on free model {free_model_id}: {e}")
            try:
                self.logger.info(f"Falling back to paid model {paid_model_id}")
                response = await self.request(
                    model_id=paid_model_id,
                    group_id=group_id,
                    prompt=prompt,
                )
                return response
            except Exception as paid_error:
                self.logger.error(
                    f"Both free and paid models failed - Free: {e}, Paid: {paid_error}"
                )
                raise
        except Exception as e:
            self.logger.error(f"AI request failed with error: {e}")
            raise

    async def chat_request(
        self,
        model_id: str,
        group_id: int,
        prompt: ConversationPrompt,
    ) -> OpenRouterResponse:
        """Make a single multi-message AI request with request tracking."""
        await self.rate_limiter.check(
            key="global_api_calls",
            limit=self.global_api_calls_per_day,
            window=timedelta(days=1),
        )

        start_time = time.time()
        try:
            response = await self.openrouter_client.chat_request(
                prompt=prompt,
                model=model_id,
            )
            await self.request_repo.create(
                Request.create(
                    telegram_group_id=group_id,
                    success=True,
                    model_openrouter_id=model_id,
                    prompt_tokens_usage=response.prompt_tokens,
                    completion_tokens_usage=response.completion_tokens,
                    cost_estimate_usd=response.cost,
                    request_payload=response.request_payload,
                    response_content=response.raw_response,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            )
            return response
        except OpenRouterRateLimitError:
            raise
        except Exception as e:
            await self.request_repo.create(
                Request.create(
                    telegram_group_id=group_id,
                    success=False,
                    model_openrouter_id=model_id,
                    request_payload={
                        "system_prompt": prompt.system,
                        "messages": prompt.messages,
                        "max_tokens": prompt.max_tokens,
                        "temperature": prompt.temperature,
                    },
                    error_message=str(e),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )
            )
            raise

    async def chat_request_with_paid_fallback(
        self,
        free_model_id: str,
        paid_model_id: str,
        group_id: int,
        prompt: ConversationPrompt,
    ) -> OpenRouterResponse:
        """Make multi-message AI request with free/paid model fallback."""
        self.logger.info(
            f"Making AI chat request with free model {free_model_id}, fallback: {paid_model_id}"
        )

        try:
            response = await self.chat_request(
                model_id=free_model_id,
                group_id=group_id,
                prompt=prompt,
            )
            return response
        except OpenRouterRateLimitError as e:
            self.logger.warning(f"Rate limited on free model {free_model_id}: {e}")
            try:
                self.logger.info(f"Falling back to paid model {paid_model_id}")
                response = await self.chat_request(
                    model_id=paid_model_id,
                    group_id=group_id,
                    prompt=prompt,
                )
                return response
            except Exception as paid_error:
                self.logger.error(
                    f"Both free and paid models failed - Free: {e}, Paid: {paid_error}"
                )
                raise
        except Exception as e:
            self.logger.error(f"AI chat request failed with error: {e}")
            raise
