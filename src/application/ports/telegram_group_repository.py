from abc import ABC, abstractmethod

from src.domain.entities import Group


class TelegramGroupRepository(ABC):
    """Port for group data access operations"""

    @abstractmethod
    async def find_by_tg_id(self, tg_id: int) -> Group | None:
        """Find group by Telegram ID.

        Args:
            tg_id: Telegram group ID

        Returns:
            Group entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_tg_id' not implemented")

    @abstractmethod
    async def find_by_id(self, telegram_group_id: int) -> Group | None:
        """Find active group by internal ID.

        Args:
            telegram_group_id: Internal group identifier

        Returns:
            Group entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_id' not implemented")

    @abstractmethod
    async def find_active_groups(self) -> list[Group]:
        """Find all active groups.

        Returns:
            List of active Group entities
        """
        raise NotImplementedError("Method 'find_active_groups' not implemented")

    @abstractmethod
    async def create(self, group: Group) -> Group:
        """Create new group entity and return the created group.

        Args:
            group: Group entity to create

        Returns:
            Created Group entity with populated primary key
        """
        raise NotImplementedError("Method 'create' not implemented")

    @abstractmethod
    async def deactivate_group(self, tg_id: int) -> None:
        """Mark group as inactive (bot removed).

        Args:
            tg_id: Telegram group ID
        """
        raise NotImplementedError("Method 'deactivate_group' not implemented")

    @abstractmethod
    async def reactivate_group(self, telegram_group_id: int, title: str) -> None:
        """Reactivate a previously deactivated group.

        Args:
            telegram_group_id: Internal group identifier
            title: Group title (possibly updated)
        """
        raise NotImplementedError("Method 'reactivate_group' not implemented")

    @abstractmethod
    async def set_language(self, telegram_group_id: int, language: str) -> None:
        """Set the detected language for a group.

        Args:
            telegram_group_id: Internal group identifier
            language: ISO language code
        """
        raise NotImplementedError("Method 'set_language' not implemented")

    @abstractmethod
    async def set_trigger_word(self, telegram_group_id: int, trigger_word: str) -> None:
        """Set trigger word for a group.

        Args:
            telegram_group_id: Internal group identifier
            trigger_word: Trigger word to set
        """
        raise NotImplementedError("Method 'set_trigger_word' not implemented")

    @abstractmethod
    async def set_persona(self, telegram_group_id: int, persona: str | None) -> None:
        """Set persona for a group, or clear it by passing None.

        Args:
            telegram_group_id: Internal group identifier
            persona: Persona text to set, or None to clear
        """
        raise NotImplementedError("Method 'set_persona' not implemented")
