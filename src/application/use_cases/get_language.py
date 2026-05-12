import logging

from src.domain.constants.bot_messages import (
    GROUP_NOT_FOUND,
    LANGUAGE_CURRENT,
    LANGUAGE_NOT_SET,
)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_bot import TelegramBotPort


class GetLanguageUseCase:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        telegram_bot: TelegramBotPort,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.telegram_bot = telegram_bot
        self.logger = logger

    async def execute(self, tg_id: int) -> None:
        group = await self.group_repo.find_by_tg_id(tg_id)

        if not group:
            self.logger.warning(f"Group not found for tg_id={tg_id}")
            await self.telegram_bot.send_message(tg_id, GROUP_NOT_FOUND)
            return

        if group.language:
            await self.telegram_bot.send_message(
                tg_id, LANGUAGE_CURRENT.format(language=group.language)
            )
        else:
            await self.telegram_bot.send_message(tg_id, LANGUAGE_NOT_SET)
