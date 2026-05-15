from abc import ABC, abstractmethod


class TelegramBotPort(ABC):
    """Port for sending messages to Telegram"""

    @abstractmethod
    async def send_message(
        self, chat_id: int, text: str, reply_to_message_id: int | None = None
    ) -> int:
        """Send a message to a Telegram chat.

        Args:
            chat_id: The chat ID to send the message to
            text: The message text to send
            reply_to_message_id: Optional message ID to reply to

        Returns:
            The message ID of the sent message
        """
        raise NotImplementedError("Method 'send_message' not implemented")
