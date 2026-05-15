import logging
import random
from datetime import datetime, timedelta

from src.domain.dto import TelegramMessage
from src.domain.entities import Group, GroupMember, Message
from src.domain.services.message_sanitization import sanitize_for_ai_prompt
from src.domain.services.suitability import evaluate_reply_suitability
from src.domain.exceptions import InternalRateLimitError
from src.domain.constants.bot_messages import RATE_LIMITED, GROUP_GREETING
from src.application.ports.task_queue import TaskQueue
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.telegram_group_member_repository import (
    TelegramGroupMemberRepository,
)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository
from src.application.ports.rate_limiter import RateLimiter
from src.application.services.message_generation_service import MessageGenerationService


class TelegramService:
    def __init__(
        self,
        follow_up_probability: float,
        reply_probability: float,
        default_trigger_word: str,
        default_language: str,
        message_repo: TelegramMessageRepository,
        group_repo: TelegramGroupRepository,
        member_repo: TelegramGroupMemberRepository,
        telegram_bot: TelegramBotPort,
        message_generation_service: MessageGenerationService,
        task_queue: TaskQueue,
        rate_limiter: RateLimiter,
        per_user_limit: int,
        per_group_limit: int,
        logger: logging.Logger,
    ):
        self.follow_up_probability = follow_up_probability
        self.reply_probability = reply_probability
        self.default_trigger_word = default_trigger_word
        self.default_language = default_language
        self.message_repo = message_repo
        self.group_repo = group_repo
        self.telegram_bot = telegram_bot
        self.member_repo = member_repo
        self.message_generation_service = message_generation_service
        self.task_queue = task_queue
        self.rate_limiter = rate_limiter
        self.per_user_limit = per_user_limit
        self.per_group_limit = per_group_limit
        self.logger = logger

    async def find_or_create_group(self, tg_id: int, title: str) -> Group:
        group = await self.group_repo.find_by_tg_id(tg_id)
        if group:
            if not group.is_active:
                await self.group_repo.reactivate_group(group.telegram_group_id, title)
        else:
            group = await self.group_repo.create(
                Group.create(
                    tg_id=tg_id,
                    title=title,
                    language=self.default_language,
                    trigger_word=self.default_trigger_word,
                )
            )
        return group

    async def find_or_create_member(
        self,
        tg_id: int,
        telegram_group_id: int,
        first_name: str,
        username: str | None,
    ) -> GroupMember:
        member = await self.member_repo.find_by_tg_and_group_id(
            tg_id, telegram_group_id
        )
        if not member:
            member = await self.member_repo.create(
                GroupMember.create(
                    telegram_group_id=telegram_group_id,
                    tg_id=tg_id,
                    first_name=first_name,
                    username=username,
                )
            )
        else:
            if member.first_name != first_name or member.username != username:
                await self.member_repo.update_member_info(
                    member.telegram_group_member_id,
                    first_name,
                    username,
                )
        return member

    async def handle_incoming_group_message(
        self, dto: TelegramMessage, bot_username: str
    ) -> None:
        group = await self.find_or_create_group(dto.chat_tg_id, dto.chat_title)
        member = await self.find_or_create_member(
            dto.user_tg_id,
            group.telegram_group_id,
            dto.user_first_name,
            dto.user_username,
        )

        sanitized_text = sanitize_for_ai_prompt(dto.message_text, group.trigger_word)

        reply_to_message_id = None
        if dto.reply_to_message_tg_id:
            reply_message = await self.message_repo.find_by_tg_id(
                group.telegram_group_id, dto.reply_to_message_tg_id
            )
            if reply_message:
                reply_to_message_id = reply_message.telegram_message_id

        should_reply = evaluate_reply_suitability(dto, group, bot_username)

        if not sanitized_text and should_reply:
            await self.telegram_bot.send_message(
                chat_id=group.tg_id,
                text=GROUP_GREETING.format(
                    trigger_word=group.trigger_word, username=bot_username
                ),
                reply_to_message_id=dto.message_tg_id,
            )
            return

        message = await self.message_repo.create(
            Message.create(
                telegram_group_id=group.telegram_group_id,
                telegram_group_member_id=member.telegram_group_member_id,
                reply_to_message_id=reply_to_message_id,
                tg_id=dto.message_tg_id,
                content=sanitized_text,
                timestamp=dto.timestamp,
                is_reply_to_bot_message=dto.is_reply_to_bot_message,
                is_generated=False,
            )
        )

        if should_reply:
            self.logger.info(
                f"Message needs reply - triggering bot reply for message {message.telegram_message_id}"
            )
            self.task_queue.queue_reply_to_message(message.telegram_message_id)
        elif (
            self.reply_probability
            and sanitized_text
            and random.random() < self.reply_probability
        ):
            self.logger.info(
                f"Message {message.telegram_message_id} randomly selected for reply"
            )
            self.task_queue.queue_reply_to_message(message.telegram_message_id, True)

    async def reply_to_message(
        self, telegram_message_id: int, randomly_selected: bool
    ) -> None:
        message = await self.message_repo.find_by_id(telegram_message_id)
        if not message:
            self.logger.warning(f"Message {telegram_message_id} not found")
            return

        group = await self.group_repo.find_by_id(message.telegram_group_id)
        if not group:
            self.logger.warning(
                f"Active group {message.telegram_group_id} not found for message {telegram_message_id}"
            )
            return

        try:
            await self.rate_limiter.check(
                key=f"user_replies:{message.telegram_group_member_id}",
                limit=self.per_user_limit,
                window=timedelta(hours=1),
            )
            await self.rate_limiter.check(
                key=f"group_replies:{group.telegram_group_id}",
                limit=self.per_group_limit,
                window=timedelta(days=1),
            )
            reply_text = await self.message_generation_service.reply_to_message(
                group, message
            )
        except InternalRateLimitError as e:
            self.logger.warning(
                f"Rate limit exceeded for replying to message {telegram_message_id}: {str(e)}"
            )
            if not randomly_selected:
                await self.telegram_bot.send_message(
                    chat_id=group.tg_id,
                    text=RATE_LIMITED,
                    reply_to_message_id=message.tg_id,
                )
            return

        if not reply_text or not reply_text.strip():
            self.logger.warning(
                f"Generated empty reply for message {telegram_message_id}, skipping"
            )
            return

        sent_message_id = await self.telegram_bot.send_message(
            chat_id=group.tg_id,
            text=reply_text,
            reply_to_message_id=message.tg_id,
        )
        generated_message = await self.message_repo.create(
            Message.create(
                telegram_group_id=group.telegram_group_id,
                telegram_group_member_id=None,
                reply_to_message_id=message.telegram_message_id,
                tg_id=sent_message_id,
                content=reply_text,
                is_reply_to_bot_message=False,
                is_generated=True,
            )
        )

        # Schedule follow-up message based on probability
        if self.follow_up_probability and random.random() < self.follow_up_probability:
            self.logger.info(
                f"Scheduling follow-up for bot message {sent_message_id} in group {group.telegram_group_id}"
            )
            delay = random.uniform(30, 60)
            self.task_queue.queue_follow_up(
                generated_message.telegram_message_id, delay
            )

    async def follow_up_message(self, telegram_message_id: int) -> None:
        bot_message = await self.message_repo.find_by_id(telegram_message_id)
        if not bot_message:
            self.logger.warning(f"Bot message {telegram_message_id} not found")
            return

        group = await self.group_repo.find_by_id(bot_message.telegram_group_id)
        if not group:
            self.logger.warning(
                f"Active group {bot_message.telegram_group_id} not found for bot message {telegram_message_id}"
            )
            return

        original_message = None
        if bot_message.reply_to_message_id:
            original_message = await self.message_repo.find_by_id(
                bot_message.reply_to_message_id
            )

        if not original_message:
            self.logger.warning(
                f"Original message not found for bot message {telegram_message_id}"
            )
            return

        try:
            follow_up_text = await self.message_generation_service.follow_up_message(
                group, original_message
            )
        except InternalRateLimitError as e:
            self.logger.warning(
                f"Rate limit exceeded for follow-up to message {telegram_message_id}: {str(e)}"
            )
            return

        if not follow_up_text or not follow_up_text.strip():
            self.logger.warning(
                f"Generated empty follow-up for bot message {telegram_message_id}, skipping"
            )
            return

        original_member = await self.member_repo.find_by_id(
            original_message.telegram_group_member_id
        )

        if original_member and original_member.username:
            follow_up_text_with_mention = (
                f"{follow_up_text} @{original_member.username}"
            )
        elif original_member:
            follow_up_text_with_mention = (
                f"{follow_up_text} {original_member.first_name}"
            )
        else:
            follow_up_text_with_mention = follow_up_text

        sent_message_id = await self.telegram_bot.send_message(
            chat_id=group.tg_id, text=follow_up_text_with_mention
        )
        await self.message_repo.create(
            Message.create(
                telegram_group_id=group.telegram_group_id,
                telegram_group_member_id=None,
                reply_to_message_id=None,
                tg_id=sent_message_id,
                content=follow_up_text,
                is_reply_to_bot_message=False,
                is_generated=True,
            )
        )
