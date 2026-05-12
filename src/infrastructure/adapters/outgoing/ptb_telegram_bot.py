import logging

from telegram import Bot

from src.application.ports.telegram_bot import TelegramBotPort


class PTBTelegramBot(TelegramBotPort):
    """Python-telegram-bot implementation of the Telegram Bot port"""

    def __init__(self, bot: Bot, logger: logging.Logger):
        self._bot = bot
        self.logger = logger

    async def send_message(
        self, chat_id: str, text: str, reply_to_message_id: str | None = None
    ) -> str:
        try:
            message = await self._bot.send_message(
                chat_id=int(chat_id),
                text=text,
                reply_to_message_id=int(reply_to_message_id)
                if reply_to_message_id
                else None,
            )

            self.logger.info(
                f"Message sent successfully to chat {chat_id}, message_id: {message.message_id}"
            )
            return str(message.message_id)

        except Exception as e:
            self.logger.error(f"Failed to send message to chat {chat_id}: {e}")
            raise
