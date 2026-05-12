import logging
from typing import Any

import httpx

from src.domain.exceptions import OpenRouterRateLimitError
from src.domain.dto import OpenRouterResponse, Prompt
from src.application.ports.openrouter_client import OpenRouterClient


class HttpxOpenRouterClient(OpenRouterClient):
    """OpenRouter API client using httpx"""

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 120.0
    MAX_CONNECTIONS = 5
    MAX_KEEPALIVE_CONNECTIONS = 2
    KEEPALIVE_EXPIRY = 60.0

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
        max_tokens: int,
        temperature: float,
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
            "max_tokens": max_tokens,
            "temperature": temperature,
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

    async def request(
        self,
        prompt: Prompt,
        max_tokens: int,
        temperature: float,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        payload = self._build_payload(
            prompt, max_tokens, temperature, model, top_p, top_k
        )

        try:
            response = await self._client.post("/chat/completions", json=payload)

            if response.status_code == 200:
                return self._parse_success_response(response.json(), payload)
            elif response.status_code == 429:
                error_msg = f"Rate limit exceeded (429): {response.text}"
                self.logger.warning(error_msg)
                raise OpenRouterRateLimitError(error_msg)
            else:
                error_msg = (
                    f"OpenRouter API error {response.status_code}: {response.text}"
                )
                self.logger.error(error_msg)
                raise Exception(error_msg)

        except httpx.TimeoutException as e:
            error_msg = f"Request timeout after {self.DEFAULT_TIMEOUT}s: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except OpenRouterRateLimitError:
            raise  # Re-raise without modification
        except httpx.HTTPError as e:
            error_msg = f"HTTP error: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
