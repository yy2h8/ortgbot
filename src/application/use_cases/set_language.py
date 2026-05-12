import logging

from src.domain.constants.bot_messages import (
    LANGUAGE_USAGE,
    GROUP_NOT_FOUND,
    LANGUAGE_SET,
    LANGUAGE_UPDATE_FAILED,
)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_bot import TelegramBotPort


class SetLanguageUseCase:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        telegram_bot: TelegramBotPort,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.telegram_bot = telegram_bot
        self.logger = logger

    async def execute(self, tg_id: int, language: str, bot_username: str) -> None:
        self.logger.info(f"Setting language for group {tg_id} to '{language}'")
        if not language or not language.strip():
            self.logger.warning(f"No language provided for group {tg_id}")
            await self.telegram_bot.send_message(
                tg_id, LANGUAGE_USAGE.format(username=bot_username)
            )
            return

        group = await self.group_repo.find_by_tg_id(tg_id)
        if not group:
            self.logger.warning(f"Group not found for tg_id={tg_id}")
            await self.telegram_bot.send_message(tg_id, GROUP_NOT_FOUND)
            return

        try:
            await self.group_repo.set_language(group.telegram_group_id, language)
            self.logger.info(f"Language updated for group {tg_id}: '{language}'")
            await self.telegram_bot.send_message(
                tg_id, LANGUAGE_SET.format(language=language)
            )
        except Exception:
            self.logger.error(f"Failed to update language for group {tg_id}")
            await self.telegram_bot.send_message(tg_id, LANGUAGE_UPDATE_FAILED)
