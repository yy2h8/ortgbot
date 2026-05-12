import logging

from src.application.ports.telegram_group_repository import TelegramGroupRepository


class BotLeftGroupUseCase:
    def __init__(
        self, group_repo: TelegramGroupRepository, logger: logging.Logger
    ) -> None:
        self.group_repo = group_repo
        self.logger = logger

    async def execute(self, tg_id: int) -> None:
        self.logger.info(f"Bot leaving group {tg_id}")
        await self.group_repo.deactivate_group(tg_id)
        self.logger.info(f"Successfully processed bot leaving group {tg_id}")
