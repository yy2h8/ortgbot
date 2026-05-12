import logging
from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide, from_context
from telegram.ext import Application

from src.infrastructure.core.settings import Settings

# Infrastructure imports
from src.infrastructure.core.database import AiosqliteDatabase
from src.infrastructure.adapters.outgoing.aiosqlite_rate_limiter import (
    AiosqliteRateLimiter,
)
from src.infrastructure.adapters.outgoing.httpx_openrouter_client import (
    HttpxOpenRouterClient,
)
from src.infrastructure.adapters.outgoing.ptb_telegram_bot import PTBTelegramBot
from src.infrastructure.adapters.outgoing.asyncio_task_queue import AsyncioTaskQueue
from src.infrastructure.adapters.outgoing.database_cleanup import DatabaseCleanup

# Repository imports
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_telegram_group_repository import (
    AiosqliteTelegramGroupRepository,
)
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_telegram_message_repository import (
    AiosqliteTelegramMessageRepository,
)
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_telegram_group_member_repository import (
    AiosqliteTelegramGroupMemberRepository,
)
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_group_context_repository import (
    AiosqliteGroupContextRepository,
)
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_group_trend_repository import (
    AiosqliteGroupTrendRepository,
)
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_openrouter_request_repository import (
    AiosqliteOpenRouterRequestRepository,
)

# Port imports (for type annotations)
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository
from src.application.ports.telegram_group_member_repository import (
    TelegramGroupMemberRepository,
)
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.group_trend_repository import GroupTrendRepository
from src.application.ports.openrouter_request_repository import (
    OpenRouterRequestRepository,
)
from src.application.ports.openrouter_client import OpenRouterClient
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.rate_limiter import RateLimiter
from src.application.ports.task_queue import TaskQueue

# Application service imports
from src.application.services.ai_service import AIService
from src.application.services.analytics_service import AnalyticsService
from src.application.services.message_generation_service import MessageGenerationService
from src.application.services.group_service import GroupService
from src.application.services.telegram_service import TelegramService

# Use case imports
from src.application.use_cases.group_joined import GroupJoinedUseCase
from src.application.use_cases.chat_message import ChatMessageUseCase
from src.application.use_cases.bot_left_group import BotLeftGroupUseCase
from src.application.use_cases.member_left_group import MemberLeftGroupUseCase
from src.application.use_cases.periodic_trends_analysis import (
    PeriodicTrendsAnalysisUseCase,
)
from src.application.use_cases.periodic_context_analysis import (
    PeriodicContextAnalysisUseCase,
)
from src.application.use_cases.reply_to_message import ReplyToMessageUseCase
from src.application.use_cases.follow_up_message import FollowUpMessageUseCase
from src.application.use_cases.set_trigger_word import SetTriggerWordUseCase
from src.application.use_cases.set_language import SetLanguageUseCase
from src.application.use_cases.get_trigger_word import GetTriggerWordUseCase
from src.application.use_cases.get_language import GetLanguageUseCase
from src.application.use_cases.set_persona import SetPersonaUseCase
from src.application.use_cases.get_persona import GetPersonaUseCase


def _get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class InfrastructureProvider(Provider):
    scope = Scope.APP
    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide
    async def get_database(
        self, settings: Settings
    ) -> AsyncGenerator[AiosqliteDatabase, None]:
        db = AiosqliteDatabase(db_path=settings.sqlite_db_path)
        yield db
        await db.close_connection()

    @provide
    def get_rate_limiter(
        self, db: AiosqliteDatabase, settings: Settings
    ) -> RateLimiter:
        return AiosqliteRateLimiter(
            db=db,
            cleanup_window_hours=settings.rate_limits_cleanup_window_hours,
            logger=_get_logger("rate_limiter"),
        )

    @provide
    async def get_openrouter_client(
        self, settings: Settings
    ) -> AsyncGenerator[OpenRouterClient, None]:
        client = HttpxOpenRouterClient(
            api_key=settings.openrouter_api_key,
            logger=_get_logger("openrouter_client"),
        )
        yield client
        await client.close()

    @provide
    def get_telegram_bot_adapter(self) -> TelegramBotPort:
        from src.infrastructure.core.ptb_lifecycle import get_application

        application = get_application()
        return PTBTelegramBot(
            bot=application.bot,
            logger=_get_logger("telegram_bot"),
        )

    @provide
    def get_database_cleanup(
        self, db: AiosqliteDatabase, settings: Settings
    ) -> DatabaseCleanup:
        return DatabaseCleanup(
            db=db,
            inactive_cleanup_days=settings.inactive_records_cleanup_days,
            logger=_get_logger("database_cleanup"),
        )


class RepositoryProvider(Provider):
    scope = Scope.APP

    @provide
    def get_telegram_group_repository(
        self, db: AiosqliteDatabase
    ) -> TelegramGroupRepository:
        return AiosqliteTelegramGroupRepository(
            db=db,
            logger=_get_logger("telegram_group_repo"),
        )

    @provide
    def get_telegram_message_repository(
        self, db: AiosqliteDatabase
    ) -> TelegramMessageRepository:
        return AiosqliteTelegramMessageRepository(
            db=db,
            logger=_get_logger("telegram_message_repo"),
        )

    @provide
    def get_telegram_group_member_repository(
        self, db: AiosqliteDatabase
    ) -> TelegramGroupMemberRepository:
        return AiosqliteTelegramGroupMemberRepository(
            db=db,
            logger=_get_logger("telegram_group_member_repo"),
        )

    @provide
    def get_group_context_repository(
        self, db: AiosqliteDatabase
    ) -> GroupContextRepository:
        return AiosqliteGroupContextRepository(
            db=db,
            logger=_get_logger("group_context_repo"),
        )

    @provide
    def get_group_trend_repository(self, db: AiosqliteDatabase) -> GroupTrendRepository:
        return AiosqliteGroupTrendRepository(
            db=db,
            logger=_get_logger("group_trend_repo"),
        )

    @provide
    def get_openrouter_request_repository(
        self, db: AiosqliteDatabase
    ) -> OpenRouterRequestRepository:
        return AiosqliteOpenRouterRequestRepository(
            db=db,
            logger=_get_logger("openrouter_request_repo"),
        )


class ServiceProvider(Provider):
    scope = Scope.APP

    @provide
    def get_ai_service(
        self,
        settings: Settings,
        openrouter_client: OpenRouterClient,
        request_repo: OpenRouterRequestRepository,
        rate_limiter: RateLimiter,
    ) -> AIService:
        return AIService(
            openrouter_client=openrouter_client,
            request_repo=request_repo,
            rate_limiter=rate_limiter,
            logger=_get_logger("ai_service"),
            global_api_calls_per_day=settings.global_api_calls_per_day,
        )

    @provide
    def get_analytics_service(
        self,
        settings: Settings,
        ai_service: AIService,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
    ) -> AnalyticsService:
        return AnalyticsService(
            ai_service=ai_service,
            message_repo=message_repo,
            trend_repo=trend_repo,
            context_repo=context_repo,
            max_trends_for_context=settings.max_trends_for_context,
            free_model_id=settings.free_model_id,
            paid_model_id=settings.paid_model_id,
            logger=_get_logger("analytics_service"),
        )

    @provide
    def get_message_generation_service(
        self,
        settings: Settings,
        ai_service: AIService,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
    ) -> MessageGenerationService:
        return MessageGenerationService(
            ai_service=ai_service,
            message_repo=message_repo,
            trend_repo=trend_repo,
            context_repo=context_repo,
            free_model_id=settings.free_model_id,
            paid_model_id=settings.paid_model_id,
            logger=_get_logger("message_generation_service"),
        )

    @provide
    def get_group_service(
        self,
        settings: Settings,
        group_repo: TelegramGroupRepository,
        message_repo: TelegramMessageRepository,
        trend_repo: GroupTrendRepository,
        context_repo: GroupContextRepository,
        analytics_service: AnalyticsService,
        telegram_bot: TelegramBotPort,
    ) -> GroupService:
        return GroupService(
            group_repo=group_repo,
            message_repo=message_repo,
            trend_repo=trend_repo,
            context_repo=context_repo,
            analytics_service=analytics_service,
            telegram_bot=telegram_bot,
            message_limit=settings.message_limit,
            max_trends_for_context=settings.max_trends_for_context,
            logger=_get_logger("group_service"),
        )


class TelegramServiceProvider(Provider):
    scope = Scope.APP

    @provide
    def get_task_queue(self) -> TaskQueue:
        return AsyncioTaskQueue(logger=_get_logger("task_queue"))

    @provide
    def get_telegram_service(
        self,
        settings: Settings,
        message_repo: TelegramMessageRepository,
        group_repo: TelegramGroupRepository,
        member_repo: TelegramGroupMemberRepository,
        telegram_bot: TelegramBotPort,
        message_generation_service: MessageGenerationService,
        task_queue: TaskQueue,
        rate_limiter: RateLimiter,
    ) -> TelegramService:
        return TelegramService(
            follow_up_probability=settings.follow_up_probability,
            reply_probability=settings.reply_probability,
            default_trigger_word=settings.trigger_word,
            default_language=settings.bot_language,
            message_repo=message_repo,
            group_repo=group_repo,
            member_repo=member_repo,
            telegram_bot=telegram_bot,
            message_generation_service=message_generation_service,
            task_queue=task_queue,
            rate_limiter=rate_limiter,
            per_user_limit=settings.per_user_replies_per_hour,
            per_group_limit=settings.per_group_replies_per_day,
            logger=_get_logger("telegram_service"),
        )


class UseCaseProvider(Provider):
    scope = Scope.APP

    @provide
    def get_group_joined_use_case(
        self,
        telegram_service: TelegramService,
        telegram_bot: TelegramBotPort,
    ) -> GroupJoinedUseCase:
        return GroupJoinedUseCase(
            telegram_service=telegram_service,
            telegram_bot=telegram_bot,
            logger=_get_logger("group_joined_use_case"),
        )

    @provide
    def get_chat_message_use_case(
        self, telegram_service: TelegramService
    ) -> ChatMessageUseCase:
        return ChatMessageUseCase(
            telegram_service=telegram_service,
            logger=_get_logger("chat_message_use_case"),
        )

    @provide
    def get_bot_left_group_use_case(
        self, group_repo: TelegramGroupRepository
    ) -> BotLeftGroupUseCase:
        return BotLeftGroupUseCase(
            group_repo=group_repo,
            logger=_get_logger("bot_left_group_use_case"),
        )

    @provide
    def get_member_left_group_use_case(
        self,
        group_repo: TelegramGroupRepository,
        member_repo: TelegramGroupMemberRepository,
    ) -> MemberLeftGroupUseCase:
        return MemberLeftGroupUseCase(
            group_repo=group_repo,
            member_repo=member_repo,
            logger=_get_logger("member_left_group_use_case"),
        )

    @provide
    def get_reply_to_message_use_case(
        self, telegram_service: TelegramService
    ) -> ReplyToMessageUseCase:
        return ReplyToMessageUseCase(
            telegram_service=telegram_service,
            logger=_get_logger("reply_to_message_use_case"),
        )

    @provide
    def get_follow_up_message_use_case(
        self, telegram_service: TelegramService
    ) -> FollowUpMessageUseCase:
        return FollowUpMessageUseCase(
            telegram_service=telegram_service,
            logger=_get_logger("follow_up_message_use_case"),
        )

    @provide
    def get_periodic_trends_analysis_use_case(
        self, group_service: GroupService
    ) -> PeriodicTrendsAnalysisUseCase:
        return PeriodicTrendsAnalysisUseCase(
            group_service=group_service,
            logger=_get_logger("periodic_trends_analysis_use_case"),
        )

    @provide
    def get_periodic_context_analysis_use_case(
        self, group_service: GroupService
    ) -> PeriodicContextAnalysisUseCase:
        return PeriodicContextAnalysisUseCase(
            group_service=group_service,
            logger=_get_logger("periodic_context_analysis_use_case"),
        )

    @provide
    def get_set_trigger_word_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> SetTriggerWordUseCase:
        return SetTriggerWordUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("set_trigger_word_use_case"),
        )

    @provide
    def get_set_language_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> SetLanguageUseCase:
        return SetLanguageUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("set_language_use_case"),
        )

    @provide
    def get_get_trigger_word_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> GetTriggerWordUseCase:
        return GetTriggerWordUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("get_trigger_word_use_case"),
        )

    @provide
    def get_get_language_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> GetLanguageUseCase:
        return GetLanguageUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("get_language_use_case"),
        )

    @provide
    def get_set_persona_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> SetPersonaUseCase:
        return SetPersonaUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("set_persona_use_case"),
        )

    @provide
    def get_get_persona_use_case(
        self, group_repo: TelegramGroupRepository, telegram_bot: TelegramBotPort
    ) -> GetPersonaUseCase:
        return GetPersonaUseCase(
            group_repo=group_repo,
            telegram_bot=telegram_bot,
            logger=_get_logger("get_persona_use_case"),
        )
