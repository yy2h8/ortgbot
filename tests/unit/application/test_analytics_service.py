import pytest
import logging
from unittest.mock import AsyncMock, MagicMock

from src.application.services.analytics_service import AnalyticsService
from src.application.services.ai_service import AIService
from src.domain.dto import ConversationPrompt, Prompt
from src.domain.exceptions import InternalRateLimitError
from tests.conftest import (
    make_group,
    make_message,
    make_group_trend,
    make_group_context,
    make_openrouter_response,
)


def _capture_prompt(mock_ai_service):
    for method in (
        "request_with_paid_fallback",
        "request",
        "chat_request_with_paid_fallback",
        "chat_request",
    ):
        call = getattr(mock_ai_service, method).call_args
        if call is not None:
            return call[1]["prompt"]
    raise AssertionError("No ai_service call captured")


def _make_analytics_service(
    ai_service=None,
    message_repo=None,
    trend_repo=None,
    context_repo=None,
    max_trends_for_context=5,
    free_model_id="test/free-model",
    paid_model_id="test/paid-model",
):
    return AnalyticsService(
        ai_service=ai_service or AsyncMock(spec=AIService),
        message_repo=message_repo or AsyncMock(),
        trend_repo=trend_repo or AsyncMock(),
        context_repo=context_repo or AsyncMock(),
        max_trends_for_context=max_trends_for_context,
        free_model_id=free_model_id,
        paid_model_id=paid_model_id,
        logger=logging.getLogger("test"),
    )


@pytest.mark.asyncio
async def test_analyze_trends_happy_path():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()

    messages = [make_message(content="hello"), make_message(content="world")]
    message_repo.get_all_messages_for_group_excluding_generated.return_value = messages
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="discussions about tech"
    )

    service = _make_analytics_service(ai_service, message_repo, trend_repo)
    group = make_group(telegram_group_id=1, language="English")
    result = await service.analyze_trends(group)

    assert result.recent_trends_text == "discussions about tech"
    assert result.analysis_message_count == 2


@pytest.mark.asyncio
async def test_analyze_trends_no_messages():
    message_repo = AsyncMock()
    message_repo.get_all_messages_for_group_excluding_generated.return_value = []

    service = _make_analytics_service(message_repo=message_repo)
    group = make_group(telegram_group_id=1)
    with pytest.raises(Exception, match="No messages found"):
        await service.analyze_trends(group)


@pytest.mark.asyncio
async def test_analyze_trends_rate_limited():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    message_repo.get_all_messages_for_group_excluding_generated.return_value = [make_message()]
    ai_service.chat_request_with_paid_fallback.side_effect = InternalRateLimitError("limited")

    service = _make_analytics_service(ai_service=ai_service, message_repo=message_repo)
    group = make_group(telegram_group_id=1, language="English")
    with pytest.raises(InternalRateLimitError):
        await service.analyze_trends(group)


@pytest.mark.asyncio
async def test_analyze_trends_no_visible_messages():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    message_repo.get_all_messages_for_group_excluding_generated.return_value = [
        make_message(content="   "),
        make_message(content="\t\n"),
    ]

    service = _make_analytics_service(ai_service=ai_service, message_repo=message_repo)
    group = make_group(telegram_group_id=1, language="English")

    with pytest.raises(Exception, match="No visible messages found for group 1"):
        await service.analyze_trends(group)

    ai_service.chat_request_with_paid_fallback.assert_not_called()
    ai_service.chat_request.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_context_happy_path_with_previous_context():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trends = [make_group_trend(), make_group_trend()]
    trend_repo.find_all_for_group.return_value = trends
    prev_ctx = make_group_context(analysis_trends_count=5, context_text="old context")
    context_repo.find_for_group.return_value = prev_ctx
    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="new context"
    )

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    group = make_group(telegram_group_id=1, language="English")
    result = await service.analyze_context(group)

    assert result.context_text == "new context"


@pytest.mark.asyncio
async def test_analyze_context_happy_path_without_previous_context():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trends = [make_group_trend(), make_group_trend()]
    trend_repo.find_all_for_group.return_value = trends
    context_repo.find_for_group.return_value = None
    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="fresh context"
    )

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=1, language="English")
    result = await service.analyze_context(group)
    assert result.context_text == "fresh context"


@pytest.mark.asyncio
async def test_analyze_context_incomplete_previous_context():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trends = [make_group_trend()]
    trend_repo.find_all_for_group.return_value = trends
    prev_ctx = make_group_context(analysis_trends_count=2)
    context_repo.find_for_group.return_value = prev_ctx
    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="ctx"
    )

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    group = make_group(telegram_group_id=1, language="English")
    result = await service.analyze_context(group)

    call_kwargs = ai_service.request_with_paid_fallback.call_args[1]
    assert "[No previous context available]" in call_kwargs["prompt"].user


@pytest.mark.asyncio
async def test_analyze_context_rate_limited():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trend_repo.find_all_for_group.return_value = [make_group_trend()]
    context_repo.find_for_group.return_value = None
    ai_service.request_with_paid_fallback.side_effect = InternalRateLimitError("limited")

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=1, language="English")
    with pytest.raises(InternalRateLimitError):
        await service.analyze_context(group)


@pytest.mark.asyncio
async def test_analyze_context_no_trends():
    trend_repo = AsyncMock()
    trend_repo.find_all_for_group.return_value = []

    service = _make_analytics_service(trend_repo=trend_repo)
    group = make_group(telegram_group_id=1)
    with pytest.raises(Exception, match="No trends found"):
        await service.analyze_context(group)


@pytest.mark.asyncio
async def test_analyze_context_trends_count_in_result():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trends = [make_group_trend(), make_group_trend(), make_group_trend()]
    trend_repo.find_all_for_group.return_value = trends
    context_repo.find_for_group.return_value = None
    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="ctx"
    )

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=1, language="English")
    result = await service.analyze_context(group)
    assert result.analysis_trends_count == 3


@pytest.mark.asyncio
async def test_analyze_trends_prompt_is_conversation_prompt_with_language_and_messages():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    message_repo.get_all_messages_for_group_excluding_generated.return_value = [
        make_message(content="Python discussion")
    ]
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="trends"
    )

    service = _make_analytics_service(ai_service=ai_service, message_repo=message_repo)
    group = make_group(telegram_group_id=1, language="French")
    await service.analyze_trends(group)

    prompt = _capture_prompt(ai_service)
    assert isinstance(prompt, ConversationPrompt)
    assert "Python discussion" in prompt.messages[0]["content"]
    assert "French" in prompt.system


@pytest.mark.asyncio
async def test_analyze_context_prompt_is_prompt_with_language_trends_and_context():
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trends = [make_group_trend(recent_trends_text="tech debates")]
    trend_repo.find_all_for_group.return_value = trends
    context_repo.find_for_group.return_value = make_group_context(
        analysis_trends_count=10, context_text="gaming community"
    )
    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="ctx"
    )

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    group = make_group(telegram_group_id=1, language="Spanish")
    await service.analyze_context(group)

    prompt = _capture_prompt(ai_service)
    assert isinstance(prompt, Prompt)
    assert "tech debates" in prompt.user
    assert "gaming community" in prompt.user
    assert "Spanish" in prompt.user


@pytest.mark.parametrize(
    "free_model_id,paid_model_id,expected_method",
    [
        ("free/model", "paid/model", "chat_request_with_paid_fallback"),
        ("free/model", None, "chat_request"),
        (None, "paid/model", "chat_request"),
    ],
)
@pytest.mark.asyncio
async def test_analyze_trends_ai_request_routing(
    free_model_id, paid_model_id, expected_method
):
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    message_repo.get_all_messages_for_group_excluding_generated.return_value = [
        make_message()
    ]

    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="trends"
    )
    ai_service.chat_request.return_value = make_openrouter_response(content="trends")

    service = _make_analytics_service(
        ai_service=ai_service,
        message_repo=message_repo,
        free_model_id=free_model_id,
        paid_model_id=paid_model_id,
    )
    group = make_group(telegram_group_id=1, language="English")
    await service.analyze_trends(group)

    getattr(ai_service, expected_method).assert_called_once()


@pytest.mark.parametrize(
    "free_model_id,paid_model_id,expected_method",
    [
        ("free/model", "paid/model", "request_with_paid_fallback"),
        ("free/model", None, "request"),
        (None, "paid/model", "request"),
    ],
)
@pytest.mark.asyncio
async def test_analyze_context_ai_request_routing(
    free_model_id, paid_model_id, expected_method
):
    ai_service = AsyncMock(spec=AIService)
    trend_repo = AsyncMock()
    context_repo = AsyncMock()
    trend_repo.find_all_for_group.return_value = [make_group_trend()]
    context_repo.find_for_group.return_value = None

    ai_service.request_with_paid_fallback.return_value = make_openrouter_response(
        content="ctx"
    )
    ai_service.request.return_value = make_openrouter_response(content="ctx")

    service = _make_analytics_service(
        ai_service=ai_service,
        trend_repo=trend_repo,
        context_repo=context_repo,
        free_model_id=free_model_id,
        paid_model_id=paid_model_id,
    )
    group = make_group(telegram_group_id=1, language="English")
    await service.analyze_context(group)

    getattr(ai_service, expected_method).assert_called_once()
