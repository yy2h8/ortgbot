import asyncio
import logging
from collections.abc import AsyncIterator

from src.domain.entities import Group
from src.domain.services.suitability import (
    evaluate_trends_suitability,
    evaluate_context_suitability,
)
from src.application.services.analytics_service import AnalyticsService
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.group_trend_repository import GroupTrendRepository


class GroupService:
    def __init__(
        self,
        group_repo: TelegramGroupRepository,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
        analytics_service: AnalyticsService,
        telegram_bot: TelegramBotPort,
        message_limit: int,
        max_trends_for_context: int,
        logger: logging.Logger,
    ):
        self.group_repo = group_repo
        self.message_repo = message_repo
        self.trend_repo = trend_repo
        self.context_repo = context_repo
        self.analytics_service = analytics_service
        self.telegram_bot = telegram_bot
        self.message_limit = message_limit
        self.max_trends_for_context = max_trends_for_context
        self.logger = logger

    async def find_suitable_groups_for_trends_analysis(self) -> AsyncIterator[Group]:
        groups = await self.group_repo.find_active_groups()
        if not groups:
            return

        group_ids = [g.telegram_group_id for g in groups]
        latest_trends, message_counts = await asyncio.gather(
            self.trend_repo.find_latest_for_groups(group_ids),
            self.message_repo.count_non_generated_for_groups(group_ids),
        )

        for group in groups:
            try:
                should_analyze_trend = evaluate_trends_suitability(
                    message_counts.get(group.telegram_group_id, 0),
                    latest_trends.get(group.telegram_group_id),
                    self.message_limit,
                )
                if should_analyze_trend:
                    yield group
            except Exception as e:
                self.logger.error(
                    f"Error checking suitability for group {group.telegram_group_id}: {e}"
                )

    async def process_group_trends_analysis(self, group: Group) -> None:
        self.logger.info(
            f"Processing trends analysis for group: {group.telegram_group_id}"
        )
        new_trend = await self.analytics_service.analyze_trends(group)
        await self.trend_repo.create(new_trend)
        if new_trend.analysis_message_count >= self.message_limit:
            await self._cleanup_after_complete_trends_analysis(group)
        self.logger.info(
            f"Successfully processed trends analysis for group {group.telegram_group_id}"
        )

    async def _cleanup_after_complete_trends_analysis(self, group: Group) -> None:
        self.logger.info(
            f"Performing cleanup for group {group.telegram_group_id} after complete trends analysis"
        )
        await asyncio.gather(
            self.trend_repo.delete_incomplete_trends(
                group.telegram_group_id, self.message_limit
            ),
            self.message_repo.delete_all_for_group(group.telegram_group_id),
        )
        self.logger.info(
            f"Completed cleanup for group {group.telegram_group_id}: deleted incomplete trends and all messages"
        )

    async def find_suitable_groups_for_context_analysis(self) -> AsyncIterator[Group]:
        groups = await self.group_repo.find_active_groups()
        if not groups:
            return

        group_ids = [g.telegram_group_id for g in groups]
        trends_counts, previous_contexts = await asyncio.gather(
            self.trend_repo.count_for_groups(group_ids),
            self.context_repo.find_for_groups(group_ids),
        )

        for group in groups:
            try:
                should_analyze_context = evaluate_context_suitability(
                    trends_counts.get(group.telegram_group_id, 0),
                    previous_contexts.get(group.telegram_group_id),
                    self.max_trends_for_context,
                )
                if should_analyze_context:
                    yield group
            except Exception as e:
                self.logger.error(
                    f"Error checking context suitability for group {group.telegram_group_id}: {e}"
                )

    async def process_group_context_analysis(self, group: Group) -> None:
        self.logger.info(
            f"Processing context analysis for group: {group.telegram_group_id}"
        )
        new_context = await self.analytics_service.analyze_context(group)
        await self.context_repo.delete_old_contexts(group.telegram_group_id)
        await self.context_repo.create(new_context)
        if new_context.analysis_trends_count >= self.max_trends_for_context:
            await self._cleanup_after_complete_context_analysis(group)
        self.logger.info(
            f"Successfully processed context analysis for group {group.telegram_group_id}"
        )

    async def _cleanup_after_complete_context_analysis(self, group: Group) -> None:
        self.logger.info(
            f"Performing cleanup for group {group.telegram_group_id} after complete context analysis"
        )
        await self.trend_repo.delete_all_for_group(group.telegram_group_id)
        self.logger.info(
            f"Completed cleanup for group {group.telegram_group_id}: deleted all trends"
        )
