import logging

from src.domain.constants.bot_messages import (
    GROUP_NOT_FOUND,
    PERSONA_SET,
    PERSONA_CLEARED,
    PERSONA_TOO_LONG,
    PERSONA_UPDATE_FAILED,
)
from src.domain.constants.defaults import MAX_PERSONA_LENGTH
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_bot import TelegramBotPort


class SetPersonaUseCase:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        telegram_bot: TelegramBotPort,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.telegram_bot = telegram_bot
        self.logger = logger

    async def execute(self, tg_id: int, persona: str | None) -> None:
        """Set or clear the persona for a group.

        Args:
            tg_id: Telegram group ID
            persona: Persona text to set, or None/empty string to clear
        """
        # Normalise: treat empty string as clearing the persona
        normalized = persona.strip() if persona else None

        if normalized and len(normalized) > MAX_PERSONA_LENGTH:
            self.logger.warning(
                f"Persona too long for group {tg_id}: {len(normalized)} chars"
            )
            await self.telegram_bot.send_message(
                tg_id, PERSONA_TOO_LONG.format(maxchars=MAX_PERSONA_LENGTH)
            )
            return

        group = await self.group_repo.find_by_tg_id(tg_id)
        if not group:
            self.logger.warning(f"Group not found for tg_id={tg_id}")
            await self.telegram_bot.send_message(tg_id, GROUP_NOT_FOUND)
            return

        try:
            await self.group_repo.set_persona(
                group.telegram_group_id, normalized or None
            )
            if normalized:
                self.logger.info(f"Persona updated for group {tg_id}")
                await self.telegram_bot.send_message(tg_id, PERSONA_SET)
            else:
                self.logger.info(f"Persona cleared for group {tg_id}")
                await self.telegram_bot.send_message(tg_id, PERSONA_CLEARED)
        except Exception:
            self.logger.error(f"Failed to update persona for group {tg_id}")
            await self.telegram_bot.send_message(tg_id, PERSONA_UPDATE_FAILED)
