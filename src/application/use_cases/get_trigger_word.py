import logging

from src.domain.constants.bot_messages import (
    GROUP_NOT_FOUND,
    TRIGGER_CURRENT,
    TRIGGER_NOT_SET,
)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_bot import TelegramBotPort


class GetTriggerWordUseCase:
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
            await self.telegram_bot.send_message(tg_id, GROUP_NOT_FOUND)
            return

        if group.trigger_word:
            await self.telegram_bot.send_message(
                tg_id, TRIGGER_CURRENT.format(trigger_word=group.trigger_word)
            )
        else:
            await self.telegram_bot.send_message(tg_id, TRIGGER_NOT_SET)
