from abc import ABC, abstractmethod

from src.domain.entities import Message


class TelegramMessageRepository(ABC):
    """Port for message data access operations."""

    @abstractmethod
    async def find_by_tg_id(self, telegram_group_id: int, tg_id: int) -> Message | None:
        """Find message by Telegram message ID.

        Args:
            telegram_group_id: Internal group identifier
            tg_id: Telegram message ID

        Returns:
            Message entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_tg_id' not implemented")

    @abstractmethod
    async def find_by_id(self, telegram_message_id: int) -> Message | None:
        """Find message by internal ID.

        Args:
            telegram_message_id: Internal message identifier

        Returns:
            Message entity if found, None otherwise
        """
        raise NotImplementedError("Method 'find_by_id' not implemented")

    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Create new message entity and return the created message.

        Args:
            message: Message entity to create

        Returns:
            Created Message entity with populated primary key
        """
        raise NotImplementedError("Method 'create' not implemented")

    @abstractmethod
    async def get_replies_for_message(self, message_id: int) -> list[Message]:
        """Get the chain of replies for a specific message in a group.

        Args:
            group_id: Internal group identifier
            message_id: Internal message identifier for which to fetch replies

        Returns:
            List of Message entities, ordered by timestamp (most recent first)
        """
        raise NotImplementedError("Method 'get_replies_for_message' not implemented")

    @abstractmethod
    async def get_all_messages_for_group_excluding_generated(
        self, group_id: int
    ) -> list[Message]:
        """Get all non-generated messages for a specific group.

        Used for trends and context analysis, excluding bot-generated messages.

        Args:
            group_id: Internal group identifier

        Returns:
            List of non-generated Message entities for the group
        """
        raise NotImplementedError(
            "Method 'get_all_messages_for_group_excluding_generated' not implemented"
        )

    @abstractmethod
    async def delete_all_for_group(self, telegram_group_id: int) -> None:
        """Delete all messages for a specific group.

        Args:
            telegram_group_id: Internal group identifier
        """
        raise NotImplementedError("Method 'delete_all_for_group' not implemented")

    @abstractmethod
    async def count_non_generated_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, int]:
        """Count non-generated messages for each of the given groups in a single query.

        Args:
            telegram_group_ids: List of internal group identifiers

        Returns:
            Dict mapping telegram_group_id to non-generated message count.
            Groups with no messages are absent from the dict.
        """
        raise NotImplementedError(
            "Method 'count_non_generated_for_groups' not implemented"
        )
