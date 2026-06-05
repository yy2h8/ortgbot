import pytest
import logging
from unittest.mock import AsyncMock, patch

from src.application.services.telegram_service import TelegramService
from src.application.services.message_generation_service import MessageGenerationService
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.task_queue import TaskQueue
from src.application.ports.rate_limiter import RateLimiter
from src.domain.constants.bot_messages import RATE_LIMITED, BOT_RATE_LIMITED
from src.domain.exceptions import InternalRateLimitError
from tests.conftest import (
    make_group,
    make_message,
    make_group_member,
    make_telegram_message,
    make_openrouter_response,
)


def _make_telegram_service(
    group_repo=None,
    message_repo=None,
    member_repo=None,
    telegram_bot=None,
    message_generation_service=None,
    task_queue=None,
    rate_limiter=None,
    follow_up_probability=0.5,
    reply_probability=0.1,
    default_trigger_word="bot",
    default_language="English",
    per_user_limit=5,
    per_group_limit=50,
    per_bot_limit=5,
):
    return TelegramService(
        follow_up_probability=follow_up_probability,
        reply_probability=reply_probability,
        default_trigger_word=default_trigger_word,
        default_language=default_language,
        message_repo=message_repo or AsyncMock(),
        group_repo=group_repo or AsyncMock(),
        member_repo=member_repo or AsyncMock(),
        telegram_bot=telegram_bot or AsyncMock(spec=TelegramBotPort),
        message_generation_service=message_generation_service or AsyncMock(spec=MessageGenerationService),
        task_queue=task_queue or AsyncMock(spec=TaskQueue),
        rate_limiter=rate_limiter or AsyncMock(spec=RateLimiter),
        per_user_limit=per_user_limit,
        per_group_limit=per_group_limit,
        per_bot_limit=per_bot_limit,
        logger=logging.getLogger("test"),
    )


@pytest.mark.asyncio
async def test_find_or_create_group_existing_active():
    group_repo = AsyncMock()
    existing = make_group(tg_id=1, telegram_group_id=10, is_active=True)
    group_repo.find_by_tg_id.return_value = existing

    service = _make_telegram_service(group_repo=group_repo)
    result = await service.find_or_create_group(1, "Test")

    assert result == existing
    group_repo.create.assert_not_called()
    group_repo.reactivate_group.assert_not_called()


@pytest.mark.asyncio
async def test_find_or_create_group_existing_inactive():
    group_repo = AsyncMock()
    existing = make_group(tg_id=1, telegram_group_id=10, is_active=False)
    group_repo.find_by_tg_id.return_value = existing

    service = _make_telegram_service(group_repo=group_repo)
    result = await service.find_or_create_group(1, "Updated Title")

    group_repo.reactivate_group.assert_called_once_with(10, "Updated Title")


@pytest.mark.asyncio
async def test_find_or_create_group_new():
    group_repo = AsyncMock()
    group_repo.find_by_tg_id.return_value = None
    created = make_group(tg_id=1, telegram_group_id=10)
    group_repo.create.return_value = created

    service = _make_telegram_service(
        group_repo=group_repo,
        default_language="English",
        default_trigger_word="bot",
    )
    result = await service.find_or_create_group(1, "New Group")

    group_repo.create.assert_called_once()
    call_arg = group_repo.create.call_args[0][0]
    assert call_arg.language == "English"
    assert call_arg.trigger_word == "bot"


@pytest.mark.asyncio
async def test_find_or_create_member_existing():
    member_repo = AsyncMock()
    existing = make_group_member(telegram_group_member_id=5)
    member_repo.find_by_tg_and_group_id.return_value = existing

    service = _make_telegram_service(member_repo=member_repo)
    result = await service.find_or_create_member(100, 1, "John", "johndoe", False)

    assert result == existing
    member_repo.update_member_info.assert_called_once()


@pytest.mark.asyncio
async def test_find_or_create_member_new():
    member_repo = AsyncMock()
    member_repo.find_by_tg_and_group_id.return_value = None
    created = make_group_member(telegram_group_member_id=5)
    member_repo.create.return_value = created

    service = _make_telegram_service(member_repo=member_repo)
    result = await service.find_or_create_member(100, 1, "John", "johndoe", False)

    member_repo.create.assert_called_once()
    call_arg = member_repo.create.call_args[0][0]
    assert call_arg.tg_id == 100
    assert call_arg.first_name == "John"
    assert call_arg.username == "johndoe"


@pytest.mark.asyncio
async def test_handle_incoming_triggers_reply():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    saved_msg = make_message(telegram_message_id=42)
    message_repo.create.return_value = saved_msg

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
    )
    dto = make_telegram_message(
        message_text="hey @mybot",
        is_reply_to_bot_message=False,
    )
    await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_handle_incoming_no_trigger_random_passes():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    saved_msg = make_message(telegram_message_id=42)
    message_repo.create.return_value = saved_msg

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
        reply_probability=0.5,
    )
    dto = make_telegram_message(message_text="hello world")

    with patch("src.application.services.telegram_service.random.random", return_value=0.1):
        await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_called_once()


@pytest.mark.asyncio
async def test_handle_incoming_no_trigger_random_fails():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    message_repo.create.return_value = make_message(telegram_message_id=42)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
        reply_probability=0.5,
    )
    dto = make_telegram_message(message_text="hello world")

    with patch("src.application.services.telegram_service.random.random", return_value=0.9):
        await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_content_sanitized():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()

    group = make_group(telegram_group_id=1, trigger_word="bot")
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
    )
    dto = make_telegram_message(message_text="email user@test.com visit https://site.com")
    await service.handle_incoming_group_message(dto, "mybot")

    call_arg = message_repo.create.call_args[0][0]
    assert "[EMAIL]" in call_arg.content
    assert "[URL]" in call_arg.content


@pytest.mark.asyncio
async def test_handle_incoming_reply_chain_resolved():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)

    target_msg = make_message(telegram_message_id=99, tg_id=555)
    message_repo.find_by_tg_id.return_value = target_msg
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
    )
    dto = make_telegram_message(reply_to_message_tg_id=555)
    await service.handle_incoming_group_message(dto, "mybot")

    message_repo.find_by_tg_id.assert_called_once_with(group.telegram_group_id, 555)
    call_arg = message_repo.create.call_args[0][0]
    assert call_arg.reply_to_message_id == 99


@pytest.mark.asyncio
async def test_handle_incoming_reply_chain_not_found():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    message_repo.find_by_tg_id.return_value = None
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
    )
    dto = make_telegram_message(reply_to_message_tg_id=999)
    await service.handle_incoming_group_message(dto, "mybot")

    message_repo.find_by_tg_id.assert_called_once_with(group.telegram_group_id, 999)
    call_arg = message_repo.create.call_args[0][0]
    assert call_arg.reply_to_message_id is None


@pytest.mark.asyncio
async def test_reply_to_message_happy_path():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    msg = make_message(telegram_message_id=1, telegram_group_id=10, tg_id=100)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    msg_gen.reply_to_message.return_value = "Hello!"
    telegram_bot.send_message.return_value = 999
    message_repo.create.return_value = make_message(telegram_message_id=2, tg_id=999)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.reply_to_message(1, randomly_selected=False)

    telegram_bot.send_message.assert_called_once()
    gen_call = message_repo.create.call_args[0][0]
    assert gen_call.is_generated is True
    assert gen_call.content == "Hello!"


@pytest.mark.asyncio
async def test_reply_to_message_not_found():
    message_repo = AsyncMock()
    message_repo.find_by_id.return_value = None

    service = _make_telegram_service(message_repo=message_repo)
    await service.reply_to_message(999, randomly_selected=False)

    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_message_group_not_found():
    message_repo = AsyncMock()
    group_repo = AsyncMock()

    msg = make_message(telegram_message_id=1, telegram_group_id=10)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = None

    service = _make_telegram_service(
        message_repo=message_repo,
        group_repo=group_repo,
    )
    await service.reply_to_message(1, randomly_selected=False)

    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_message_empty_reply():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    msg = make_message(telegram_message_id=1, telegram_group_id=10)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    msg_gen.reply_to_message.return_value = ""

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.reply_to_message(1, randomly_selected=False)

    telegram_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_message_follow_up_scheduled():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    task_queue = AsyncMock(spec=TaskQueue)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    msg = make_message(telegram_message_id=1, telegram_group_id=10, tg_id=100)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    msg_gen.reply_to_message.return_value = "Hello!"
    telegram_bot.send_message.return_value = 999
    gen_msg = make_message(telegram_message_id=50, tg_id=999)
    message_repo.create.return_value = gen_msg

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        task_queue=task_queue,
        message_generation_service=msg_gen,
        follow_up_probability=0.5,
    )

    with patch("src.application.services.telegram_service.random.random", return_value=0.1), \
         patch("src.application.services.telegram_service.random.uniform", return_value=20.0):
        await service.reply_to_message(1, randomly_selected=False)

    task_queue.queue_follow_up.assert_called_once_with(50, 20.0)


@pytest.mark.asyncio
async def test_reply_to_message_follow_up_not_scheduled():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    task_queue = AsyncMock(spec=TaskQueue)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    msg = make_message(telegram_message_id=1, telegram_group_id=10, tg_id=100)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    msg_gen.reply_to_message.return_value = "Hello!"
    telegram_bot.send_message.return_value = 999
    message_repo.create.return_value = make_message(telegram_message_id=50)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        task_queue=task_queue,
        message_generation_service=msg_gen,
        follow_up_probability=0.5,
    )

    with patch("src.application.services.telegram_service.random.random", return_value=0.9):
        await service.reply_to_message(1, randomly_selected=False)

    task_queue.queue_follow_up.assert_not_called()


@pytest.mark.asyncio
async def test_follow_up_with_username():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=1,
    )
    original_msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=5,
        telegram_group_id=10,
    )
    group = make_group(telegram_group_id=10, tg_id=500)
    member = make_group_member(telegram_group_member_id=5, username="johndoe")

    message_repo.find_by_id.side_effect = lambda id: {
        2: bot_msg,
        1: original_msg,
    }.get(id)
    group_repo.find_by_id.return_value = group
    member_repo.find_by_id.return_value = member
    msg_gen.follow_up_message.return_value = "Also, check this"
    telegram_bot.send_message.return_value = 1000
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.follow_up_message(2)

    send_call = telegram_bot.send_message.call_args
    assert "@johndoe" in send_call[1]["text"]


@pytest.mark.asyncio
async def test_follow_up_without_username():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=1,
    )
    original_msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=5,
        telegram_group_id=10,
    )
    group = make_group(telegram_group_id=10, tg_id=500)
    member = make_group_member(telegram_group_member_id=5, first_name="John", username=None)

    message_repo.find_by_id.side_effect = lambda id: {
        2: bot_msg,
        1: original_msg,
    }.get(id)
    group_repo.find_by_id.return_value = group
    member_repo.find_by_id.return_value = member
    msg_gen.follow_up_message.return_value = "Also, check this"
    telegram_bot.send_message.return_value = 1000
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.follow_up_message(2)

    send_call = telegram_bot.send_message.call_args
    assert "John" in send_call[1]["text"]


@pytest.mark.asyncio
async def test_follow_up_member_not_found():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=1,
    )
    original_msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=5,
        telegram_group_id=10,
    )
    group = make_group(telegram_group_id=10, tg_id=500)

    message_repo.find_by_id.side_effect = lambda id: {
        2: bot_msg,
        1: original_msg,
    }.get(id)
    group_repo.find_by_id.return_value = group
    member_repo.find_by_id.return_value = None
    msg_gen.follow_up_message.return_value = "Also check this"
    telegram_bot.send_message.return_value = 1000
    message_repo.create.return_value = make_message()

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.follow_up_message(2)

    send_call = telegram_bot.send_message.call_args
    assert send_call[1]["text"] == "Also check this"


@pytest.mark.asyncio
async def test_follow_up_bot_message_not_found():
    message_repo = AsyncMock()
    message_repo.find_by_id.return_value = None

    service = _make_telegram_service(message_repo=message_repo)
    await service.follow_up_message(999)

    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_follow_up_group_not_found():
    message_repo = AsyncMock()
    group_repo = AsyncMock()

    bot_msg = make_message(telegram_message_id=2, telegram_group_id=10)
    message_repo.find_by_id.return_value = bot_msg
    group_repo.find_by_id.return_value = None

    service = _make_telegram_service(
        message_repo=message_repo,
        group_repo=group_repo,
    )
    await service.follow_up_message(2)

    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_follow_up_original_message_not_found():
    message_repo = AsyncMock()
    group_repo = AsyncMock()

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=None,
    )
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = bot_msg
    group_repo.find_by_id.return_value = group

    service = _make_telegram_service(
        message_repo=message_repo,
        group_repo=group_repo,
    )
    await service.follow_up_message(2)

    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_follow_up_empty_follow_up():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=1,
    )
    original_msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=5,
        telegram_group_id=10,
    )
    group = make_group(telegram_group_id=10, tg_id=500)

    message_repo.find_by_id.side_effect = lambda id: {
        2: bot_msg,
        1: original_msg,
    }.get(id)
    group_repo.find_by_id.return_value = group
    msg_gen.follow_up_message.return_value = "   "

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.follow_up_message(2)

    telegram_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_message_rate_limited():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)
    rate_limiter = AsyncMock(spec=RateLimiter)

    msg = make_message(telegram_message_id=1, telegram_group_id=10, tg_id=100)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    rate_limiter.check.side_effect = InternalRateLimitError("rate limited")

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
        rate_limiter=rate_limiter,
    )
    await service.reply_to_message(1, randomly_selected=False)

    msg_gen.reply_to_message.assert_not_called()
    telegram_bot.send_message.assert_called_once()
    send_call = telegram_bot.send_message.call_args
    assert send_call[1]["text"] == RATE_LIMITED


@pytest.mark.asyncio
async def test_follow_up_message_rate_limited():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)

    bot_msg = make_message(
        telegram_message_id=2,
        telegram_group_id=10,
        reply_to_message_id=1,
    )
    original_msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=5,
        telegram_group_id=10,
    )
    group = make_group(telegram_group_id=10, tg_id=500)

    message_repo.find_by_id.side_effect = lambda id: {
        2: bot_msg,
        1: original_msg,
    }.get(id)
    group_repo.find_by_id.return_value = group
    msg_gen.follow_up_message.side_effect = InternalRateLimitError("rate limited")

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
    )
    await service.follow_up_message(2)

    telegram_bot.send_message.assert_not_called()
    message_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_empty_text_triggers_greeting():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1, trigger_word="bot")
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        task_queue=task_queue,
    )
    dto = make_telegram_message(message_text="bot")
    await service.handle_incoming_group_message(dto, "mybot")

    message_repo.create.assert_not_called()
    task_queue.queue_reply_to_message.assert_not_called()
    send_call = telegram_bot.send_message.call_args
    assert send_call[1]["reply_to_message_id"] == dto.message_tg_id
    assert "trigger_word" in send_call[1]["text"] or "bot" in send_call[1]["text"]


@pytest.mark.asyncio
async def test_reply_to_message_rate_limited_randomly_selected_silent():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    msg_gen = AsyncMock(spec=MessageGenerationService)
    rate_limiter = AsyncMock(spec=RateLimiter)

    msg = make_message(telegram_message_id=1, telegram_group_id=10, tg_id=100)
    group = make_group(telegram_group_id=10, tg_id=500)
    message_repo.find_by_id.return_value = msg
    group_repo.find_by_id.return_value = group
    rate_limiter.check.side_effect = InternalRateLimitError("rate limited")

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        telegram_bot=telegram_bot,
        message_generation_service=msg_gen,
        rate_limiter=rate_limiter,
    )
    await service.reply_to_message(1, randomly_selected=True)

    msg_gen.reply_to_message.assert_not_called()
    telegram_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_find_or_create_member_unchanged_no_update():
    member_repo = AsyncMock()
    existing = make_group_member(
        telegram_group_member_id=5,
        tg_id=100,
        first_name="John",
        username="johndoe",
    )
    member_repo.find_by_tg_and_group_id.return_value = existing

    service = _make_telegram_service(member_repo=member_repo)
    result = await service.find_or_create_member(100, 1, "John", "johndoe", False)

    assert result == existing
    member_repo.update_member_info.assert_not_called()
    member_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_random_reply_passes_flag():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    saved_msg = make_message(telegram_message_id=42)
    message_repo.create.return_value = saved_msg

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
        reply_probability=0.5,
    )
    dto = make_telegram_message(message_text="hello world")

    with patch("src.application.services.telegram_service.random.random", return_value=0.1):
        await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_called_once_with(42, True)


@pytest.mark.asyncio
async def test_handle_incoming_reply_probability_zero():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(telegram_group_member_id=5)
    message_repo.create.return_value = make_message(telegram_message_id=42)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
        reply_probability=0,
    )
    dto = make_telegram_message(message_text="hello world")
    await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_bot_trigger_rate_limited():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    rate_limiter = AsyncMock(spec=RateLimiter)
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(
        telegram_group_member_id=5, is_bot=True
    )
    message_repo.create.return_value = make_message(telegram_message_id=42)
    rate_limiter.check.side_effect = InternalRateLimitError("bot rate limited")

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        rate_limiter=rate_limiter,
        task_queue=task_queue,
    )
    dto = make_telegram_message(
        message_text="hey @mybot",
        user_is_bot=True,
    )
    await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_not_called()
    send_call = telegram_bot.send_message.call_args
    assert send_call[1]["text"] == BOT_RATE_LIMITED.format(bot_name="Test")
    assert send_call[1].get("reply_to_message_id") is None


@pytest.mark.asyncio
async def test_handle_incoming_bot_random_rate_limited_silent():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    telegram_bot = AsyncMock(spec=TelegramBotPort)
    rate_limiter = AsyncMock(spec=RateLimiter)
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(
        telegram_group_member_id=5, is_bot=True
    )
    message_repo.create.return_value = make_message(telegram_message_id=42)
    rate_limiter.check.side_effect = InternalRateLimitError("bot rate limited")

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        telegram_bot=telegram_bot,
        rate_limiter=rate_limiter,
        task_queue=task_queue,
        reply_probability=0.5,
    )
    dto = make_telegram_message(message_text="hello world", user_is_bot=True)

    with patch("src.application.services.telegram_service.random.random", return_value=0.1):
        await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_not_called()
    telegram_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_bot_not_rate_limited():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(
        telegram_group_member_id=5, is_bot=True
    )
    message_repo.create.return_value = make_message(telegram_message_id=42)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        task_queue=task_queue,
    )
    dto = make_telegram_message(
        message_text="hey @mybot",
        user_is_bot=True,
    )
    await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_handle_incoming_human_skips_bot_rate_limit():
    group_repo = AsyncMock()
    message_repo = AsyncMock()
    member_repo = AsyncMock()
    rate_limiter = AsyncMock(spec=RateLimiter)
    task_queue = AsyncMock(spec=TaskQueue)

    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = make_group_member(
        telegram_group_member_id=5, is_bot=False
    )
    message_repo.create.return_value = make_message(telegram_message_id=42)

    service = _make_telegram_service(
        group_repo=group_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        rate_limiter=rate_limiter,
        task_queue=task_queue,
    )
    dto = make_telegram_message(
        message_text="hey @mybot",
        user_is_bot=False,
    )
    await service.handle_incoming_group_message(dto, "mybot")

    task_queue.queue_reply_to_message.assert_called_once_with(42)
    rate_limiter.check.assert_not_called()


@pytest.mark.asyncio
async def test_find_or_create_member_updates_is_bot():
    member_repo = AsyncMock()
    existing = make_group_member(
        telegram_group_member_id=5,
        tg_id=100,
        first_name="Mira",
        username="mira",
        is_bot=False,
    )
    member_repo.find_by_tg_and_group_id.return_value = existing

    service = _make_telegram_service(member_repo=member_repo)
    result = await service.find_or_create_member(100, 1, "Mira", "mira", True)

    member_repo.update_member_info.assert_called_once_with(5, "Mira", "mira", True)
