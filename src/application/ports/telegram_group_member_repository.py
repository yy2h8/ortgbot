from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities import GroupMember


class TelegramGroupMemberRepository(ABC):
    """Port for group member data access operations"""

    @abstractmethod
    async def find_by_tg_and_group_id(
        self, tg_id: int, telegram_group_id: int
    ) -> GroupMember | None:
        """Find member by Telegram user ID and group ID.

        Args:
            tg_id: Telegram user ID
            telegram_group_id: Internal group identifier

        Returns:
            GroupMember entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_tg_and_group_id' not implemented")

    @abstractmethod
    async def find_by_id(self, telegram_group_member_id: int) -> GroupMember | None:
        """Find member by internal ID.

        Args:
            telegram_group_member_id: Internal member identifier

        Returns:
            GroupMember entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_id' not implemented")

    @abstractmethod
    async def create(self, member: GroupMember) -> GroupMember:
        """Create new member entity and return the created entity.

        Args:
            member: GroupMember entity to create

        Returns:
            Created GroupMember entity with populated primary key
        """
        raise NotImplementedError("Method 'create' not implemented")

    @abstractmethod
    async def update_member_info(
        self,
        telegram_group_member_id: int,
        first_name: str,
        username: str | None,
        is_bot: bool,
    ) -> None:
        """Update member profile information.

        Args:
            telegram_group_member_id: Internal member identifier
            first_name: User's first name
            username: User's username (optional)
            is_bot: Whether the member is a bot
        """
        raise NotImplementedError("Method 'update_member_info' not implemented")

    @abstractmethod
    async def mark_member_left(self, telegram_group_member_id: int) -> None:
        """Mark member as having left group.

        Args:
            telegram_group_member_id: Internal member identifier
        """
        raise NotImplementedError("Method 'mark_member_left' not implemented")
