import asyncio
import logging
import random
from typing import Any

import httpx

from src.domain.exceptions import EmptyResponseError, OpenRouterRateLimitError
from src.domain.dto import OpenRouterResponse, Prompt, ConversationPrompt
from src.application.ports.openrouter_client import OpenRouterClient


class HttpxOpenRouterClient(OpenRouterClient):
    """OpenRouter API client using httpx.

    Transient failures (timeouts, connection errors, HTTP 5xx, malformed
    responses, empty content) are retried up to MAX_RETRIES times with
    full-jitter exponential backoff.

    Errors that are never retried:
      - HTTP 429 → raises OpenRouterRateLimitError immediately (triggers paid-model
        fallback in AIService)
      - HTTP 4xx (other than 429) → raises Exception immediately (client errors
        won't self-heal)
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 45.0
    MAX_CONNECTIONS = 5
    MAX_KEEPALIVE_CONNECTIONS = 2
    KEEPALIVE_EXPIRY = 60.0

    # Retry configuration
    MAX_RETRIES = 3           # 4 total attempts (initial + 3 retries)
    RETRY_BACKOFF_BASE = 2.0  # seconds
    RETRY_BACKOFF_MAX = 30.0  # seconds cap

    def __init__(
        self,
        api_key: str,
        logger: logging.Logger,
    ):
        self._api_key = api_key
        self.logger = logger
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.DEFAULT_TIMEOUT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            limits=httpx.Limits(
                max_connections=self.MAX_CONNECTIONS,
                max_keepalive_connections=self.MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=self.KEEPALIVE_EXPIRY,
            ),
        )

    async def close(self) -> None:
        """Release the underlying connection pool.  Called by the Dishka
        provider during container shutdown."""
        await self._client.aclose()

    @staticmethod
    def _build_payload(
        prompt: Prompt,
        model: str,
        top_p: float | None,
        top_k: int | None,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "max_tokens": prompt.max_tokens,
            "temperature": prompt.temperature,
            "reasoning": {"effort": "none"},
        }

        if top_p is not None:
            payload["top_p"] = top_p
        if top_k is not None:
            payload["top_k"] = top_k

        return payload

    @staticmethod
    def _build_chat_payload(
        prompt: ConversationPrompt,
        model: str,
        top_p: float | None,
        top_k: int | None,
    ) -> dict[str, Any]:
        messages = [{"role": "system", "content": prompt.system}] + prompt.messages
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": prompt.max_tokens,
            "temperature": prompt.temperature,
            "reasoning": {"effort": "none"},
        }

        if top_p is not None:
            payload["top_p"] = top_p
        if top_k is not None:
            payload["top_k"] = top_k

        return payload

    @staticmethod
    def _parse_success_response(
        response_data: dict, request_payload: dict
    ) -> OpenRouterResponse:
        usage = response_data.get("usage", {})
        choices = response_data.get("choices", [])
        content = (choices[0]["message"]["content"] if choices else "") or ""

        return OpenRouterResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw_response=response_data,
            request_payload=request_payload,
            cost=float(usage.get("cost", 0)),
        )

    def _jitter_sleep(self, attempt: int) -> float:
        cap = min(self.RETRY_BACKOFF_MAX, self.RETRY_BACKOFF_BASE ** (attempt + 1))
        return random.uniform(0, cap)

    async def _execute_with_retry(self, payload: dict) -> OpenRouterResponse:
        total_attempts = self.MAX_RETRIES + 1
        last_exc: Exception = Exception("No attempts made")

        for attempt in range(total_attempts):
            retriable_exc: Exception | None = None

            try:
                response = await self._client.post("/chat/completions", json=payload)

                if response.status_code == 200:
                    # Wrap parsing so a malformed 200 body is retried, not
                    # propagated as an unexpected exception.
                    try:
                        data = response.json()
                        parsed = self._parse_success_response(data, payload)
                    except (ValueError, KeyError, IndexError) as e:
                        retriable_exc = Exception(
                            f"Malformed OpenRouter response: {e}"
                        )
                    else:
                        if not parsed.content:
                            retriable_exc = EmptyResponseError(
                                "OpenRouter returned empty content"
                            )
                        else:
                            return parsed

                elif response.status_code == 429:
                    error_msg = (
                        f"Rate limit exceeded (429): "
                        f"{response.text[:100]}..."
                    )
                    self.logger.warning(error_msg)
                    raise OpenRouterRateLimitError(error_msg)

                elif response.status_code >= 500:
                    retriable_exc = Exception(
                        f"OpenRouter server error {response.status_code}: "
                        f"{response.text[:100]}..."
                    )

                else:
                    # 4xx (non-429): client error, won't self-heal — raise immediately
                    error_msg = (
                        f"OpenRouter API error {response.status_code}: "
                        f"{response.text[:100]}..."
                    )
                    self.logger.error(error_msg)
                    raise Exception(error_msg)

            except OpenRouterRateLimitError:
                raise  # propagate immediately for paid-model fallback

            # Store the original httpx exception directly: preserves exception
            # type, message, and traceback context for upstream callers.
            except httpx.TimeoutException as e:
                retriable_exc = e

            except httpx.HTTPError as e:
                retriable_exc = e

            # Explicit guard: retriable_exc must be set at this point.
            # Any code path that didn't set it either returned, raised
            # OpenRouterRateLimitError, or raised a fatal 4xx Exception —
            # none of which reach here.
            if retriable_exc is None:
                raise RuntimeError(
                    "BUG: retry loop reached post-attempt block "
                    "without setting retriable_exc"
                )

            last_exc = retriable_exc

            if attempt < self.MAX_RETRIES:
                sleep_s = self._jitter_sleep(attempt)
                self.logger.warning(
                    f"Transient error on attempt {attempt + 1}/{total_attempts}: "
                    f"{last_exc}. Retrying in {sleep_s:.1f}s."
                )
                await asyncio.sleep(sleep_s)

        raise last_exc

    async def request(
        self,
        prompt: Prompt,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        payload = self._build_payload(prompt, model, top_p, top_k)
        return await self._execute_with_retry(payload)

    async def chat_request(
        self,
        prompt: ConversationPrompt,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        payload = self._build_chat_payload(prompt, model, top_p, top_k)
        return await self._execute_with_retry(payload)
