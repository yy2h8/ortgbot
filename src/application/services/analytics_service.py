import asyncio
import logging

from src.domain.entities import GroupContext, GroupTrend, Group
from src.domain.dto import OpenRouterResponse, ConversationPrompt, Prompt
from src.domain.constants.prompt_templates import (
    ANALYZE_CONTEXT_TEMPLATE,
    ANALYZE_TRENDS_TEMPLATE,
)
from src.domain.services.formatting import format_trends_for_prompt
from src.domain.services.conversation_formatting import build_conversation_messages
from src.domain.exceptions import InternalRateLimitError
from src.application.services.ai_service import AIService
from src.application.ports.group_trend_repository import GroupTrendRepository
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository


class AnalyticsService:
    def __init__(
        self,
        ai_service: AIService,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
        max_trends_for_context: int,
        free_model_id: str | None,
        paid_model_id: str | None,
        logger: logging.Logger,
    ):
        self.ai_service = ai_service
        self.message_repo = message_repo
        self.trend_repo = trend_repo
        self.context_repo = context_repo
        self.max_trends_for_context = max_trends_for_context
        self.free_model_id = free_model_id
        self.paid_model_id = paid_model_id
        self.logger = logger

    async def _make_ai_request(
        self,
        prompt: Prompt,
        group_id: int,
    ) -> OpenRouterResponse:
        if self.free_model_id and self.paid_model_id:
            return await self.ai_service.request_with_paid_fallback(
                free_model_id=self.free_model_id,
                paid_model_id=self.paid_model_id,
                group_id=group_id,
                prompt=prompt,
            )
        model_id = self.free_model_id or self.paid_model_id
        return await self.ai_service.request(
            model_id=model_id,
            group_id=group_id,
            prompt=prompt,
        )

    async def _make_ai_chat_request(
        self,
        prompt: ConversationPrompt,
        group_id: int,
    ) -> OpenRouterResponse:
        if self.free_model_id and self.paid_model_id:
            return await self.ai_service.chat_request_with_paid_fallback(
                free_model_id=self.free_model_id,
                paid_model_id=self.paid_model_id,
                group_id=group_id,
                prompt=prompt,
            )
        model_id = self.free_model_id or self.paid_model_id
        return await self.ai_service.chat_request(
            model_id=model_id,
            group_id=group_id,
            prompt=prompt,
        )

    async def analyze_context(self, group: Group) -> GroupContext:
        all_trends, previous_context = await asyncio.gather(
            self.trend_repo.find_all_for_group(group.telegram_group_id),
            self.context_repo.find_for_group(group.telegram_group_id),
        )

        if not all_trends:
            raise Exception(f"No trends found for group {group.telegram_group_id}")

        formatted_trends = format_trends_for_prompt(all_trends)
        if (
            previous_context
            and previous_context.analysis_trends_count >= self.max_trends_for_context
        ):
            formatted_context = previous_context.context_text
        else:
            formatted_context = "[No previous context available]"

        prompt = ANALYZE_CONTEXT_TEMPLATE.render(
            language=group.language,
            trends=formatted_trends,
            context=formatted_context,
        )

        try:
            response = await self._make_ai_request(
                prompt=prompt,
                group_id=group.telegram_group_id,
            )
        except InternalRateLimitError as e:
            self.logger.warning(
                f"Rate limited on context analysis request for group {group.telegram_group_id}: {e}"
            )
            raise

        return GroupContext.create(
            telegram_group_id=group.telegram_group_id,
            context_text=response.content.strip(),
            analysis_trends_count=len(all_trends),
        )

    async def analyze_trends(self, group: Group) -> GroupTrend:
        messages = (
            await self.message_repo.get_all_messages_for_group_excluding_generated(
                group.telegram_group_id
            )
        )

        if not messages:
            raise Exception(f"No messages found for group {group.telegram_group_id}")

        conversation_messages = build_conversation_messages(messages)
        if not conversation_messages:
            raise Exception(
                f"No visible messages found for group {group.telegram_group_id}"
            )

        prompt = ANALYZE_TRENDS_TEMPLATE.render(
            messages=conversation_messages,
            language=group.language,
        )

        try:
            response = await self._make_ai_chat_request(
                prompt=prompt,
                group_id=group.telegram_group_id,
            )
        except InternalRateLimitError as e:
            self.logger.warning(
                f"Rate limited on trends analysis request for group {group.telegram_group_id}: {e}"
            )
            raise

        return GroupTrend.create(
            telegram_group_id=group.telegram_group_id,
            recent_trends_text=response.content.strip(),
            analysis_message_count=len(messages),
        )
