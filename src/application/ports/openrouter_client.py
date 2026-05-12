from abc import ABC, abstractmethod

from src.domain.dto import OpenRouterResponse, Prompt


class OpenRouterClient(ABC):
    """Port for making requests to the OpenRouter API"""

    @abstractmethod
    async def request(
        self,
        prompt: Prompt,
        max_tokens: int,
        temperature: float,
        model: str,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> OpenRouterResponse:
        """Make a request to OpenRouter API with fallback support.

        Args:
            prompt: The prompt containing system and user instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            model: OpenRouter model id
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            top_k: Top-k sampling parameter

        Returns:
            OpenRouterResponse containing the API response with usage statistics, content, etc.

        Raises:
            OpenRouterRateLimitError: When API returns 429 rate limit
            Exception: If request fails or other errors occur
        """
        raise NotImplementedError("Method 'request' not implemented")
