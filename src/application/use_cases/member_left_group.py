import logging

from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_group_member_repository import (
    TelegramGroupMemberRepository,
)


class MemberLeftGroupUseCase:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        member_repo: TelegramGroupMemberRepository,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.member_repo = member_repo
        self.logger = logger

    async def execute(self, chat_tg_id: int, user_tg_id: int) -> None:
        self.logger.info(f"Member {user_tg_id} left group {chat_tg_id}")

        group = await self.group_repo.find_by_tg_id(chat_tg_id)
        if not group:
            self.logger.warning(
                f"Cannot mark member {user_tg_id} as left - group {chat_tg_id} not found"
            )
            return

        member = await self.member_repo.find_by_tg_and_group_id(
            user_tg_id, group.telegram_group_id
        )
        if not member:
            self.logger.warning(
                f"Cannot mark member {user_tg_id} as left - member not found in group {group.telegram_group_id}"
            )
            return

        await self.member_repo.mark_member_left(member.telegram_group_member_id)
        self.logger.info(
            f"Successfully processed member {user_tg_id} leaving group {chat_tg_id}"
        )
