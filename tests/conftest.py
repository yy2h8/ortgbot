from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from src.domain.entities import (
    Group,
    GroupMember,
    Message,
    GroupContext,
    GroupTrend,
    Request,
)
from src.domain.dto import TelegramMessage, OpenRouterResponse, Prompt, ConversationPrompt
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.openrouter_client import OpenRouterClient
from src.application.ports.openrouter_request_repository import (
    OpenRouterRequestRepository,
)
from src.application.ports.rate_limiter import RateLimiter
from src.application.ports.task_queue import TaskQueue
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_message_repository import (
    TelegramMessageRepository,
)
from src.application.ports.telegram_group_member_repository import (
    TelegramGroupMemberRepository,
)
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.group_trend_repository import GroupTrendRepository


def make_group(**overrides):
    defaults = dict(
        tg_id=1,
        title="Test Group",
        language="English",
        trigger_word="bot",
        persona=None,
    )
    defaults.update(overrides)
    return Group.create(**defaults)


def make_message(**overrides):
    defaults = dict(
        telegram_group_id=1,
        tg_id=100,
        content="Hello world",
        is_reply_to_bot_message=False,
        is_generated=False,
        timestamp=datetime(2024, 1, 1, 16, 34, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Message.create(**defaults)


def make_group_member(**overrides):
    defaults = dict(
        telegram_group_id=1,
        tg_id=100,
        first_name="Test",
    )
    defaults.update(overrides)
    return GroupMember.create(**defaults)


def make_group_trend(**overrides):
    defaults = dict(
        telegram_group_id=1,
        recent_trends_text="Some trends",
        analysis_message_count=10,
    )
    defaults.update(overrides)
    return GroupTrend.create(**defaults)


def make_group_context(**overrides):
    defaults = dict(
        telegram_group_id=1,
        context_text="Some context",
        analysis_trends_count=3,
    )
    defaults.update(overrides)
    return GroupContext.create(**defaults)


def make_request(**overrides):
    defaults = dict(
        telegram_group_id=1,
    )
    defaults.update(overrides)
    return Request.create(**defaults)


def make_telegram_message(**overrides):
    defaults = dict(
        chat_tg_id=1,
        chat_title="Test Group",
        user_tg_id=100,
        user_first_name="Test",
        user_username=None,
        user_is_bot=False,
        message_tg_id=200,
        message_text="Hello",
        reply_to_message_tg_id=None,
        timestamp=datetime.now(timezone.utc),
        is_reply_to_bot_message=False,
    )
    defaults.update(overrides)
    return TelegramMessage(**defaults)


def make_openrouter_response(**overrides):
    defaults = dict(
        content="AI response",
        prompt_tokens=100,
        completion_tokens=50,
        raw_response={},
        request_payload={},
        cost=0.001,
    )
    defaults.update(overrides)
    return OpenRouterResponse(**defaults)


def make_prompt(**overrides):
    defaults = dict(
        system="sys",
        user="usr",
        temperature=0.5,
        max_tokens=100,
    )
    defaults.update(overrides)
    return Prompt(**defaults)


def make_conversation_prompt(**overrides):
    defaults = dict(
        system="sys",
        messages=[{"role": "user", "content": "[user_1]: hello"}],
        temperature=0.9,
        max_tokens=100,
    )
    defaults.update(overrides)
    return ConversationPrompt(**defaults)


async def async_iter(items):
    """Helper to wrap a list into an async iterator for mocking async generators."""
    for item in items:
        yield item


@pytest.fixture
def mock_telegram_bot():
    return AsyncMock(spec=TelegramBotPort)


@pytest.fixture
def mock_openrouter_client():
    return AsyncMock(spec=OpenRouterClient)


@pytest.fixture
def mock_openrouter_request_repo():
    return AsyncMock(spec=OpenRouterRequestRepository)


@pytest.fixture
def mock_rate_limiter():
    return AsyncMock(spec=RateLimiter)


@pytest.fixture
def mock_task_queue():
    return AsyncMock(spec=TaskQueue)


@pytest.fixture
def mock_group_repo():
    return AsyncMock(spec=TelegramGroupRepository)


@pytest.fixture
def mock_message_repo():
    return AsyncMock(spec=TelegramMessageRepository)


@pytest.fixture
def mock_member_repo():
    return AsyncMock(spec=TelegramGroupMemberRepository)


@pytest.fixture
def mock_context_repo():
    return AsyncMock(spec=GroupContextRepository)


@pytest.fixture
def mock_trend_repo():
    return AsyncMock(spec=GroupTrendRepository)
