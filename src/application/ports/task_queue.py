from abc import ABC, abstractmethod


class TaskQueue(ABC):
    """Port for background task execution"""

    @abstractmethod
    def queue_reply_to_message(
        self, telegram_message_id: int, randomly_selected: bool = False
    ) -> None:
        """Queue a reply-to-message task for background execution.

        Args:
            telegram_message_id: ID of the message to reply to
            randomly_selected: Whether the message was randomly selected for reply
        """
        raise NotImplementedError("Method 'queue_reply_to_message' not implemented")

    @abstractmethod
    def queue_follow_up(self, telegram_message_id: int, delay: float) -> None:
        """Queue a follow-up message task for background execution with delay.

        Args:
            telegram_message_id: ID of the bot's previous message
            delay: Delay in seconds before sending follow-up
        """
        raise NotImplementedError("Method 'queue_follow_up' not implemented")
