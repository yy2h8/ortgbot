from abc import ABC, abstractmethod

from src.domain.entities import Request


class OpenRouterRequestRepository(ABC):
    """Port for OpenRouter request data access operations"""

    @abstractmethod
    async def create(self, request: Request) -> None:
        """Create a new OpenRouter request.

        Args:
            request: Request entity to create
        """
        raise NotImplementedError("Method 'create' not implemented")
