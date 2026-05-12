import asyncio
import logging

from src.domain.entities import Group, Message
from src.domain.dto import OpenRouterResponse
from src.domain.constants.prompt_templates import (
    REPLY_TO_MESSAGE_TEMPLATE,
    FOLLOW_UP_TEMPLATE,
)
from src.domain.constants.defaults import DEFAULT_PERSONA
from src.domain.services.conversation_formatting import format_conversation_for_prompt
from src.domain.services.formatting import strip_paired_quotes, truncate_for_prompt
from src.application.services.ai_service import AIService
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.group_trend_repository import GroupTrendRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository


class MessageGenerationService:
    MAX_TOKENS = 100
    TEMPERATURE = 0.9

    def __init__(
        self,
        ai_service: AIService,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
        free_model_id: str | None,
        paid_model_id: str | None,
        logger: logging.Logger,
    ):
        self.ai_service = ai_service
        self.message_repo = message_repo
        self.trend_repo = trend_repo
        self.context_repo = context_repo
        self.free_model_id = free_model_id
        self.paid_model_id = paid_model_id
        self.logger = logger

    async def _prepare_context(
        self, group: Group, target_message: Message
    ) -> tuple[str, str, str]:
        messages, recent_trend, context = await asyncio.gather(
            self.message_repo.get_replies_for_message(
                message_id=target_message.telegram_message_id,
            ),
            self.trend_repo.find_latest_for_group(group.telegram_group_id),
            self.context_repo.find_for_group(group.telegram_group_id),
        )

        if not messages:
            raise Exception(f"No messages found for group {group.telegram_group_id}")
        conversation = format_conversation_for_prompt(messages)

        formatted_trend = (
            recent_trend.recent_trends_text
            if recent_trend
            else "[No recent trends available]"
        )
        formatted_context = (
            context.context_text if context else "[No context available]"
        )

        return conversation, formatted_trend, formatted_context

    async def _make_ai_request(
        self,
        prompt,
        group_id: int,
    ) -> OpenRouterResponse:
        if self.free_model_id and self.paid_model_id:
            return await self.ai_service.request_with_paid_fallback(
                free_model_id=self.free_model_id,
                paid_model_id=self.paid_model_id,
                group_id=group_id,
                prompt=prompt,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
            )
        model_id = self.free_model_id or self.paid_model_id
        return await self.ai_service.request(
            model_id=model_id,
            group_id=group_id,
            prompt=prompt,
            max_tokens=self.MAX_TOKENS,
            temperature=self.TEMPERATURE,
        )

    async def reply_to_message(self, group: Group, message: Message) -> str:
        conversation, trends, context = await self._prepare_context(group, message)
        truncated_message = truncate_for_prompt(message.content)
        prompt = REPLY_TO_MESSAGE_TEMPLATE.render(
            language=group.language,
            persona=group.persona or DEFAULT_PERSONA,
            recent_trend=trends,
            context=context,
            message=truncated_message,
            conversation=conversation,
        )
        response = await self._make_ai_request(
            prompt=prompt,
            group_id=group.telegram_group_id,
        )
        return strip_paired_quotes(response.content)

    async def follow_up_message(self, group: Group, original_message: Message) -> str:
        conversation, trends, context = await self._prepare_context(
            group, original_message
        )
        truncated_original_message = truncate_for_prompt(original_message.content)
        prompt = FOLLOW_UP_TEMPLATE.render(
            language=group.language,
            persona=group.persona or DEFAULT_PERSONA,
            recent_trend=trends,
            context=context,
            original_message=truncated_original_message,
            conversation=conversation,
        )
        response = await self._make_ai_request(
            prompt=prompt,
            group_id=group.telegram_group_id,
        )
        return strip_paired_quotes(response.content)
