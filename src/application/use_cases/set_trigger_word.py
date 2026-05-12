import logging

from src.domain.constants.bot_messages import (
    TRIGGER_USAGE,
    GROUP_NOT_FOUND,
    TRIGGER_SET,
    TRIGGER_UPDATE_FAILED,
)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_bot import TelegramBotPort


class SetTriggerWordUseCase:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        telegram_bot: TelegramBotPort,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.telegram_bot = telegram_bot
        self.logger = logger

    async def execute(self, tg_id: int, trigger_word: str, bot_username: str) -> None:
        self.logger.info(f"Setting trigger word for group {tg_id} to '{trigger_word}'")
        if not trigger_word or not trigger_word.strip():
            self.logger.warning(f"No trigger word provided for group {tg_id}")
            await self.telegram_bot.send_message(
                tg_id, TRIGGER_USAGE.format(username=bot_username)
            )
            return

        group = await self.group_repo.find_by_tg_id(tg_id)
        if not group:
            self.logger.warning(f"Active group not found for tg_id={tg_id}")
            await self.telegram_bot.send_message(tg_id, GROUP_NOT_FOUND)
            return

        try:
            await self.group_repo.set_trigger_word(
                group.telegram_group_id, trigger_word.lower()
            )
            self.logger.info(
                f"Trigger word updated for group {tg_id}: '{trigger_word}'"
            )
            await self.telegram_bot.send_message(
                tg_id, TRIGGER_SET.format(trigger_word=trigger_word)
            )
        except Exception:
            self.logger.error(f"Failed to update trigger word for group {tg_id}")
            await self.telegram_bot.send_message(tg_id, TRIGGER_UPDATE_FAILED)
