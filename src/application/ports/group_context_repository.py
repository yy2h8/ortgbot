from abc import ABC, abstractmethod

from src.domain.entities import GroupContext


class GroupContextRepository(ABC):
    """Port for group context data access operations"""

    @abstractmethod
    async def create(self, group_context: GroupContext) -> GroupContext:
        """Create new group context entity and return the created entity.

        Args:
            group_context: GroupContext entity to create

        Returns:
            The created GroupContext entity with populated primary key field
        """
        raise NotImplementedError("Method 'create' not implemented")

    @abstractmethod
    async def find_for_group(self, telegram_group_id: int) -> GroupContext | None:
        """Find the latest created context for a group.

        Args:
            telegram_group_id: Internal group identifier

        Returns:
            GroupContext entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_for_group' not implemented")

    @abstractmethod
    async def delete_old_contexts(self, telegram_group_id: int) -> None:
        """Delete all existing contexts for a group (keeping only one at a time).

        Args:
            telegram_group_id: Internal group identifier
        """
        raise NotImplementedError("Method 'delete_old_contexts' not implemented")

    @abstractmethod
    async def find_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, "GroupContext"]:
        """Find the latest context for each of the given groups in a single query.

        Args:
            telegram_group_ids: List of internal group identifiers

        Returns:
            Dict mapping telegram_group_id to the latest GroupContext for that group.
            Groups with no context are absent from the dict.
        """
        raise NotImplementedError("Method 'find_for_groups' not implemented")
