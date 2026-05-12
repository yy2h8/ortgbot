import logging

from src.domain.dto import TelegramMessage
from src.application.services.telegram_service import TelegramService


class ChatMessageUseCase:
    def __init__(self, telegram_service: TelegramService, logger: logging.Logger):
        self.service = telegram_service
        self.logger = logger

    async def execute(self, dto: TelegramMessage, bot_username: str) -> None:
        self.logger.info(
            f"Handling chat message from group {dto.chat_tg_id}, user {dto.user_tg_id}"
        )
        await self.service.handle_incoming_group_message(dto, bot_username)
        self.logger.debug(f"Successfully processed chat message {dto.message_tg_id}")
