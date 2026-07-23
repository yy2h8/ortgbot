import pytest
import logging
from unittest.mock import AsyncMock

from src.application.services.message_generation_service import MessageGenerationService
from src.application.services.ai_service import AIService
from src.domain.dto import ConversationPrompt
from src.domain.constants.defaults import DEFAULT_PERSONA
from tests.conftest import (
    make_group,
    make_message,
    make_group_trend,
    make_group_context,
    make_openrouter_response,
    make_conversation_prompt,
)


def _make_service(
    ai_service=None,
    message_repo=None,
    trend_repo=None,
    context_repo=None,
    free_model_id="free/model",
    paid_model_id="paid/model",
):
    return MessageGenerationService(
        ai_service=ai_service or AsyncMock(spec=AIService),
        message_repo=message_repo or AsyncMock(),
        trend_repo=trend_repo or AsyncMock(),
        context_repo=context_repo or AsyncMock(),
        free_model_id=free_model_id,
        paid_model_id=paid_model_id,
        logger=logging.getLogger("test"),
    )


def _setup_context_mocks(message_repo, trend_repo, context_repo, messages=None, trend=None, context=None):
    message_repo.get_replies_for_message.return_value = messages or [make_message(telegram_message_id=1)]
    trend_repo.find_latest_for_group.return_value = trend
    context_repo.find_for_group.return_value = context


@pytest.mark.asyncio
async def test_reply_to_message_happy_path():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trend = make_group_trend(recent_trends_text="sports talk")
    context = make_group_context(context_text="sports group")
    _setup_context_mocks(
        message_repo, trend_repo, context_repo,
        messages=[make_message(telegram_message_id=1, content="hello")],
        trend=trend,
        context=context,
    )
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="nice goal")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona="funny guy")
    message = make_message(telegram_message_id=1, content="did you see the game?")

    result = await service.reply_to_message(group, message)

    assert result == "nice goal"
    ai_service.chat_request_with_paid_fallback.assert_called_once()
    call_kwargs = ai_service.chat_request_with_paid_fallback.call_args[1]
    assert call_kwargs["free_model_id"] == "free/model"
    assert call_kwargs["paid_model_id"] == "paid/model"
    assert call_kwargs["group_id"] == 10
    assert isinstance(call_kwargs["prompt"], ConversationPrompt)


@pytest.mark.asyncio
async def test_reply_to_message_persona_fallback():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(message_repo, trend_repo, context_repo)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="hey")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona=None)
    message = make_message(telegram_message_id=1, content="sup")

    await service.reply_to_message(group, message)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert DEFAULT_PERSONA in prompt.system


@pytest.mark.asyncio
async def test_reply_to_message_custom_persona():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(message_repo, trend_repo, context_repo)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="yo")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona="sarcastic nerd")
    message = make_message(telegram_message_id=1, content="hi")

    await service.reply_to_message(group, message)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert "sarcastic nerd" in prompt.system
    assert DEFAULT_PERSONA not in prompt.system


@pytest.mark.asyncio
async def test_reply_to_message_strips_outer_quotes():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(message_repo, trend_repo, context_repo)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content='"quoted response"'
    )

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    message = make_message(telegram_message_id=1, content="hi")

    result = await service.reply_to_message(group, message)

    assert result == "quoted response"


@pytest.mark.asyncio
async def test_reply_to_message_no_outer_quotes_unchanged():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(message_repo, trend_repo, context_repo)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="plain response"
    )

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    message = make_message(telegram_message_id=1, content="hi")

    result = await service.reply_to_message(group, message)

    assert result == "plain response"


@pytest.mark.asyncio
async def test_follow_up_message_happy_path():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trend = make_group_trend(recent_trends_text="discussing movies")
    context = make_group_context(context_text="movie buffs")
    _setup_context_mocks(
        message_repo, trend_repo, context_repo,
        messages=[make_message(telegram_message_id=1, content="original")],
        trend=trend,
        context=context,
    )
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="also the soundtrack was great"
    )

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona="movie nerd")
    original = make_message(telegram_message_id=1, content="the plot was thin")

    result = await service.follow_up_message(group, original)

    assert result == "also the soundtrack was great"
    ai_service.chat_request_with_paid_fallback.assert_called_once()
    call_kwargs = ai_service.chat_request_with_paid_fallback.call_args[1]
    assert call_kwargs["group_id"] == 10
    assert isinstance(call_kwargs["prompt"], ConversationPrompt)


@pytest.mark.asyncio
async def test_follow_up_message_uses_bot_message_as_last_assistant_turn():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    bot_message = make_message(
        telegram_message_id=2,
        telegram_group_member_id=None,
        is_generated=True,
        content="that movie ending was cheap",
        reply_to_message_id=1,
    )
    _setup_context_mocks(
        message_repo,
        trend_repo,
        context_repo,
        messages=[
            make_message(telegram_message_id=1, telegram_group_member_id=5, content="hot take"),
            bot_message,
        ],
        trend=make_group_trend(recent_trends_text="movie debate"),
        context=make_group_context(context_text="film club"),
    )
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(
        content="and the pacing was worse"
    )

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona="movie nerd")

    await service.follow_up_message(group, bot_message)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert prompt.messages[-1] == {
        "role": "assistant",
        "content": "that movie ending was cheap",
    }


@pytest.mark.asyncio
async def test_follow_up_message_persona_fallback():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(message_repo, trend_repo, context_repo)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="hmm")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10, persona=None)
    original = make_message(telegram_message_id=1, content="hey")

    await service.follow_up_message(group, original)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert DEFAULT_PERSONA in prompt.system


@pytest.mark.asyncio
async def test_follow_up_message_no_trend_uses_fallback():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(
        message_repo, trend_repo, context_repo,
        trend=None,
        context=make_group_context(context_text="some context"),
    )
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="ok")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    original = make_message(telegram_message_id=1, content="hey")

    await service.follow_up_message(group, original)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert "[No recent trends available]" in prompt.system


@pytest.mark.asyncio
async def test_follow_up_message_no_context_uses_fallback():
    ai_service = AsyncMock(spec=AIService)
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    _setup_context_mocks(
        message_repo, trend_repo, context_repo,
        trend=make_group_trend(recent_trends_text="some trend"),
        context=None,
    )
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response(content="ok")

    service = _make_service(
        ai_service=ai_service,
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    original = make_message(telegram_message_id=1, content="hey")

    await service.follow_up_message(group, original)

    prompt = ai_service.chat_request_with_paid_fallback.call_args[1]["prompt"]
    assert "[No context available]" in prompt.system


@pytest.mark.asyncio
async def test_prepare_context_calls_all_repos_concurrently():
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    messages = [make_message(telegram_message_id=1, content="hi")]
    trend = make_group_trend(recent_trends_text="trend text")
    context = make_group_context(context_text="context text")
    _setup_context_mocks(message_repo, trend_repo, context_repo, messages=messages, trend=trend, context=context)

    service = _make_service(
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    target = make_message(telegram_message_id=5)

    conversation, formatted_trend, formatted_context = await service._prepare_context(group, target)

    message_repo.get_replies_for_message.assert_called_once_with(message_id=5)
    trend_repo.find_latest_for_group.assert_called_once_with(10)
    context_repo.find_for_group.assert_called_once_with(10)
    assert formatted_trend == "trend text"
    assert formatted_context == "context text"


@pytest.mark.asyncio
async def test_prepare_context_no_messages_raises():
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    message_repo.get_replies_for_message.return_value = []
    trend_repo.find_latest_for_group.return_value = None
    context_repo.find_for_group.return_value = None

    service = _make_service(
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    target = make_message(telegram_message_id=5)

    with pytest.raises(Exception, match="No messages found for group 10"):
        await service._prepare_context(group, target)


@pytest.mark.asyncio
async def test_prepare_context_no_visible_messages_raises():
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    message_repo.get_replies_for_message.return_value = [
        make_message(telegram_message_id=1, content="   "),
        make_message(telegram_message_id=2, content="\t\n"),
    ]
    trend_repo.find_latest_for_group.return_value = None
    context_repo.find_for_group.return_value = None

    service = _make_service(
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    target = make_message(telegram_message_id=5)

    with pytest.raises(Exception, match="No visible messages found for group 10"):
        await service._prepare_context(group, target)


@pytest.mark.asyncio
async def test_prepare_context_trend_and_context_both_present():
    message_repo = AsyncMock()
    trend_repo = AsyncMock()
    context_repo = AsyncMock()

    trend = make_group_trend(recent_trends_text="gaming talk")
    context = make_group_context(context_text="gamer group")
    _setup_context_mocks(
        message_repo, trend_repo, context_repo,
        messages=[make_message(telegram_message_id=1, content="msg")],
        trend=trend,
        context=context,
    )

    service = _make_service(
        message_repo=message_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    group = make_group(telegram_group_id=10)
    target = make_message(telegram_message_id=5)

    conversation, formatted_trend, formatted_context = await service._prepare_context(group, target)

    assert formatted_trend == "gaming talk"
    assert formatted_context == "gamer group"
    assert "msg" in conversation[0]["content"]


@pytest.mark.asyncio
async def test_make_ai_chat_request_both_models_uses_fallback():
    ai_service = AsyncMock(spec=AIService)
    ai_service.chat_request_with_paid_fallback.return_value = make_openrouter_response()

    service = _make_service(
        ai_service=ai_service,
        free_model_id="free/model",
        paid_model_id="paid/model",
    )
    prompt = make_conversation_prompt()

    await service._make_ai_chat_request(prompt=prompt, group_id=5)

    ai_service.chat_request_with_paid_fallback.assert_called_once()
    ai_service.chat_request.assert_not_called()


@pytest.mark.asyncio
async def test_make_ai_chat_request_only_free_model():
    ai_service = AsyncMock(spec=AIService)
    ai_service.chat_request.return_value = make_openrouter_response()

    service = _make_service(
        ai_service=ai_service,
        free_model_id="free/model",
        paid_model_id=None,
    )
    prompt = make_conversation_prompt()

    await service._make_ai_chat_request(prompt=prompt, group_id=5)

    ai_service.chat_request.assert_called_once()
    call_kwargs = ai_service.chat_request.call_args[1]
    assert call_kwargs["model_id"] == "free/model"


@pytest.mark.asyncio
async def test_make_ai_chat_request_only_paid_model():
    ai_service = AsyncMock(spec=AIService)
    ai_service.chat_request.return_value = make_openrouter_response()

    service = _make_service(
        ai_service=ai_service,
        free_model_id=None,
        paid_model_id="paid/model",
    )
    prompt = make_conversation_prompt()

    await service._make_ai_chat_request(prompt=prompt, group_id=5)

    ai_service.chat_request.assert_called_once()
    call_kwargs = ai_service.chat_request.call_args[1]
    assert call_kwargs["model_id"] == "paid/model"


@pytest.mark.asyncio
async def test_make_ai_chat_request_neither_model():
    ai_service = AsyncMock(spec=AIService)
    ai_service.chat_request.return_value = make_openrouter_response()

    service = _make_service(
        ai_service=ai_service,
        free_model_id=None,
        paid_model_id=None,
    )
    prompt = make_conversation_prompt()

    await service._make_ai_chat_request(prompt=prompt, group_id=5)

    ai_service.chat_request.assert_called_once()
    call_kwargs = ai_service.chat_request.call_args[1]
    assert call_kwargs["model_id"] is None
