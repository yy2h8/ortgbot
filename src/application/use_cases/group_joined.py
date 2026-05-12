import logging

from src.domain.constants.bot_messages import GROUP_GREETING
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.services.telegram_service import TelegramService


class GroupJoinedUseCase:
    def __init__(
        self,
        telegram_service: TelegramService,
        telegram_bot: TelegramBotPort,
        logger: logging.Logger,
    ):
        self.telegram_service = telegram_service
        self.telegram_bot = telegram_bot
        self.logger = logger

    async def execute(self, tg_id: int, title: str, bot_username: str) -> None:
        self.logger.info(f"Bot joined group {title} (ID: {tg_id})")
        group = await self.telegram_service.find_or_create_group(tg_id, title)
        self.logger.info(
            f"Successfully processed group join for {title}, group ID: {group.telegram_group_id}"
        )
        await self.telegram_bot.send_message(
            tg_id,
            GROUP_GREETING.format(
                trigger_word=group.trigger_word, username=bot_username
            ),
        )
        self.logger.info(f"Greeting sent to group {title}")
