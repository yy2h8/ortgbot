import logging

from src.application.services.telegram_service import TelegramService


class ReplyToMessageUseCase:
    def __init__(self, telegram_service: TelegramService, logger: logging.Logger):
        self.telegram_service = telegram_service
        self.logger = logger

    async def execute(self, telegram_message_id: int, randomly_selected: bool) -> None:
        self.logger.info(f"Generating reply for message {telegram_message_id}")
        await self.telegram_service.reply_to_message(
            telegram_message_id, randomly_selected
        )
        self.logger.debug(f"Successfully sent reply to message {telegram_message_id}")
