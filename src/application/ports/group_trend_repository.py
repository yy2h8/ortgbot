from abc import ABC, abstractmethod

from src.domain.entities import GroupTrend


class GroupTrendRepository(ABC):
    """Port for group trend data access operations"""

    @abstractmethod
    async def create(self, group_trend: GroupTrend) -> GroupTrend:
        """Create new group trend entity and return the created entity.

        Args:
            group_trend: GroupTrend entity to create

        Returns:
            Created GroupTrend entity with populated primary key
        """
        raise NotImplementedError("Method 'create' not implemented")

    @abstractmethod
    async def find_latest_for_group(self, telegram_group_id: int) -> GroupTrend | None:
        """Find latest created trend for a group.

        Args:
            telegram_group_id: Internal group identifier

        Returns:
            GroupTrend entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_latest_for_group' not implemented")

    @abstractmethod
    async def delete_incomplete_trends(
        self, telegram_group_id: int, message_limit: int
    ) -> None:
        """Delete all trends for a group that have analysis_message_count less than limit.

        Args:
            telegram_group_id: Internal group identifier
            message_limit: Minimum message count threshold
        """
        raise NotImplementedError("Method 'delete_incomplete_trends' not implemented")

    @abstractmethod
    async def find_all_for_group(self, telegram_group_id: int) -> list[GroupTrend]:
        """Find all trends for a group.

        Args:
            telegram_group_id: Internal group identifier

        Returns:
            List of GroupTrend entities for group
        """
        raise NotImplementedError("Method 'find_all_for_group' not implemented")

    @abstractmethod
    async def find_latest_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, "GroupTrend"]:
        """Find the latest trend for each of the given groups in a single query.

        Args:
            telegram_group_ids: List of internal group identifiers

        Returns:
            Dict mapping telegram_group_id to the latest GroupTrend for that group.
            Groups with no trends are absent from the dict.
        """
        raise NotImplementedError("Method 'find_latest_for_groups' not implemented")

    @abstractmethod
    async def count_for_groups(self, telegram_group_ids: list[int]) -> dict[int, int]:
        """Count trends for each of the given groups in a single query.

        Args:
            telegram_group_ids: List of internal group identifiers

        Returns:
            Dict mapping telegram_group_id to trend count.
            Groups with no trends are absent from the dict.
        """
        raise NotImplementedError("Method 'count_for_groups' not implemented")

    @abstractmethod
    async def delete_all_for_group(self, telegram_group_id: int) -> None:
        """Delete all trends for a group except most recent one.

        Args:
            telegram_group_id: Internal group identifier
        """
        raise NotImplementedError("Method 'delete_all_for_group' not implemented")
