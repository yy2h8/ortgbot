import logging

from telegram import Bot

from src.application.ports.telegram_bot import TelegramBotPort


class PTBTelegramBot(TelegramBotPort):
    """Python-telegram-bot implementation of the Telegram Bot port"""

    def __init__(self, bot: Bot, logger: logging.Logger):
        self._bot = bot
        self.logger = logger

    async def send_message(
        self, chat_id: int, text: str, reply_to_message_id: int | None = None
    ) -> int:
        try:
            message = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
            )

            self.logger.info(
                f"Message sent successfully to chat {chat_id}, message_id: {message.message_id}"
            )
            return message.message_id

        except Exception as e:
            self.logger.error(f"Failed to send message to chat {chat_id}: {e}")
            raise
