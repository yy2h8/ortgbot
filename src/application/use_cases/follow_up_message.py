import logging

from src.application.services.telegram_service import TelegramService


class FollowUpMessageUseCase:
    def __init__(self, telegram_service: TelegramService, logger: logging.Logger):
        self.telegram_service = telegram_service
        self.logger = logger

    async def execute(self, telegram_message_id: int) -> None:
        self.logger.info(f"Handling follow-up for message {telegram_message_id}")
        await self.telegram_service.follow_up_message(telegram_message_id)
        self.logger.debug(
            f"Successfully processed follow-up for message {telegram_message_id}"
        )
