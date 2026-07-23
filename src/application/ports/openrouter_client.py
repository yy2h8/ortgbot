from abc import ABC, abstractmethod

from src.domain.dto import OpenRouterResponse, Prompt, ConversationPrompt


class OpenRouterClient(ABC):
    """Port for making requests to the OpenRouter API"""

    @abstractmethod
    async def request(
        self,
        prompt: Prompt,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        """Make a request to OpenRouter API with fallback support.

        temperature and max_tokens come from the prompt.
        Implementations should retry on transient failures (timeouts, connection
        errors, HTTP 5xx, empty response content) with exponential backoff before
        raising.

        Args:
            prompt: The prompt containing system and user instructions
            model: OpenRouter model id
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            top_k: Top-k sampling parameter

        Returns:
            OpenRouterResponse containing the API response with usage statistics, content, etc.

        Raises:
            OpenRouterRateLimitError: When API returns 429 — raised immediately so
                the caller can fall back to a paid model.
            EmptyResponseError: When all retry attempts return empty content.
            Exception: For non-retriable client errors (4xx) or when all retries
                are exhausted on transient failures.
        """
        raise NotImplementedError("Method 'request' not implemented")

    @abstractmethod
    async def chat_request(
        self,
        prompt: ConversationPrompt,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        """Make a multi-message request. temperature and max_tokens come from prompt.
        Same retry/error contract as request().
        """
        raise NotImplementedError("Method 'chat_request' not implemented")
