import pytest
import logging
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.chat_message import ChatMessageUseCase
from src.application.use_cases.reply_to_message import ReplyToMessageUseCase
from src.application.use_cases.follow_up_message import FollowUpMessageUseCase
from src.application.use_cases.group_joined import GroupJoinedUseCase
from src.application.use_cases.bot_left_group import BotLeftGroupUseCase
from src.application.use_cases.member_left_group import MemberLeftGroupUseCase
from src.application.use_cases.set_trigger_word import SetTriggerWordUseCase
from src.application.use_cases.set_language import SetLanguageUseCase
from src.application.use_cases.get_trigger_word import GetTriggerWordUseCase
from src.application.use_cases.get_language import GetLanguageUseCase
from src.application.use_cases.set_persona import SetPersonaUseCase
from src.application.use_cases.get_persona import GetPersonaUseCase
from src.application.use_cases.periodic_trends_analysis import PeriodicTrendsAnalysisUseCase
from src.application.use_cases.periodic_context_analysis import PeriodicContextAnalysisUseCase
from src.application.services.telegram_service import TelegramService
from src.application.services.group_service import GroupService
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_group_member_repository import TelegramGroupMemberRepository
from src.domain.constants.bot_messages import GROUP_GREETING
from src.domain.constants.defaults import MAX_PERSONA_LENGTH
from tests.conftest import make_group, make_group_member, make_telegram_message, async_iter


def _logger():
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_chat_message_delegates():
    ts = AsyncMock(spec=TelegramService)
    uc = ChatMessageUseCase(telegram_service=ts, logger=_logger())
    dto = make_telegram_message()
    await uc.execute(dto, "mybot")
    ts.handle_incoming_group_message.assert_called_once_with(dto, "mybot")


@pytest.mark.asyncio
async def test_reply_to_message_delegates():
    ts = AsyncMock(spec=TelegramService)
    uc = ReplyToMessageUseCase(telegram_service=ts, logger=_logger())
    await uc.execute(42, randomly_selected=False)
    ts.reply_to_message.assert_called_once_with(42, False)


@pytest.mark.asyncio
async def test_follow_up_delegates():
    ts = AsyncMock(spec=TelegramService)
    uc = FollowUpMessageUseCase(telegram_service=ts, logger=_logger())
    await uc.execute(42)
    ts.follow_up_message.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_group_joined_creates_and_greets():
    ts = AsyncMock(spec=TelegramService)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(trigger_word="bot")
    ts.find_or_create_group.return_value = group

    uc = GroupJoinedUseCase(telegram_service=ts, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "Test Group", "mybot")

    ts.find_or_create_group.assert_called_once_with(123, "Test Group")
    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args
    assert call_args[0][0] == 123
    assert "bot" in call_args[0][1]
    assert "mybot" in call_args[0][1]


@pytest.mark.asyncio
async def test_bot_left_group_deactivates():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    uc = BotLeftGroupUseCase(group_repo=group_repo, logger=_logger())
    await uc.execute(123)
    group_repo.deactivate_group.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_member_left_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    member_repo = AsyncMock(spec=TelegramGroupMemberRepository)
    group_repo.find_by_tg_id.return_value = None

    uc = MemberLeftGroupUseCase(group_repo=group_repo, member_repo=member_repo, logger=_logger())
    await uc.execute(123, 456)
    member_repo.mark_member_left.assert_not_called()


@pytest.mark.asyncio
async def test_member_left_member_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    member_repo = AsyncMock(spec=TelegramGroupMemberRepository)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = None

    uc = MemberLeftGroupUseCase(group_repo=group_repo, member_repo=member_repo, logger=_logger())
    await uc.execute(123, 456)
    member_repo.mark_member_left.assert_not_called()


@pytest.mark.asyncio
async def test_member_left_happy_path():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    member_repo = AsyncMock(spec=TelegramGroupMemberRepository)
    group = make_group(telegram_group_id=1)
    member = make_group_member(telegram_group_member_id=5)
    group_repo.find_by_tg_id.return_value = group
    member_repo.find_by_tg_and_group_id.return_value = member

    uc = MemberLeftGroupUseCase(group_repo=group_repo, member_repo=member_repo, logger=_logger())
    await uc.execute(123, 456)
    member_repo.mark_member_left.assert_called_once_with(5)


@pytest.mark.asyncio
async def test_set_trigger_empty_word():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    uc = SetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "", "mybot")
    bot.send_message.assert_called_once()
    assert "Usage" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_trigger_whitespace_only():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    uc = SetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "   ", "mybot")
    bot.send_message.assert_called_once()
    assert "Usage" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_trigger_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = SetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "hello", "mybot")
    bot.send_message.assert_called_once()
    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_trigger_success():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "Hello", "mybot")

    group_repo.set_trigger_word.assert_called_once_with(1, "hello")
    assert "Hello" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_trigger_repo_exception():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    group_repo.set_trigger_word.side_effect = Exception("db error")

    uc = SetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "hello", "mybot")

    bot.send_message.assert_called_once()
    assert "Failed" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_language_empty():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    uc = SetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "", "mybot")
    bot.send_message.assert_called_once()
    assert "Usage" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_language_whitespace_only():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    uc = SetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "   ", "mybot")
    bot.send_message.assert_called_once()
    assert "Usage" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_language_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = SetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "French", "mybot")
    bot.send_message.assert_called_once()
    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_language_success():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "French", "mybot")

    group_repo.set_language.assert_called_once_with(1, "French")
    assert "French" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_language_repo_exception():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    group_repo.set_language.side_effect = Exception("db error")

    uc = SetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "French", "mybot")

    bot.send_message.assert_called_once()
    assert "Failed" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_get_trigger_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = GetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    bot.send_message.assert_called_once()
    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_get_trigger_has_trigger():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(trigger_word="bot")
    group_repo.find_by_tg_id.return_value = group

    uc = GetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    assert "bot" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_get_trigger_no_trigger():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(trigger_word="")
    group_repo.find_by_tg_id.return_value = group

    uc = GetTriggerWordUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    assert "No trigger" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_get_language_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = GetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    bot.send_message.assert_called_once()
    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_get_language_has_language():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(language="English")
    group_repo.find_by_tg_id.return_value = group

    uc = GetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    assert "English" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_get_language_no_language():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(language="")
    group_repo.find_by_tg_id.return_value = group

    uc = GetLanguageUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)
    assert "No language" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_periodic_trends_analysis():
    gs = AsyncMock(spec=GroupService)
    g1 = make_group(telegram_group_id=1)
    g2 = make_group(telegram_group_id=2)
    gs.find_suitable_groups_for_trends_analysis = Mock(return_value=async_iter([g1, g2]))

    uc = PeriodicTrendsAnalysisUseCase(group_service=gs, logger=_logger())
    await uc.execute()

    assert gs.process_group_trends_analysis.call_count == 2


@pytest.mark.asyncio
async def test_periodic_trends_analysis_continues_on_error():
    gs = AsyncMock(spec=GroupService)
    g1 = make_group(telegram_group_id=1)
    g2 = make_group(telegram_group_id=2)
    gs.find_suitable_groups_for_trends_analysis = Mock(return_value=async_iter([g1, g2]))
    gs.process_group_trends_analysis.side_effect = [Exception("error"), None]

    uc = PeriodicTrendsAnalysisUseCase(group_service=gs, logger=_logger())
    await uc.execute()

    assert gs.process_group_trends_analysis.call_count == 2


@pytest.mark.asyncio
async def test_periodic_context_analysis():
    gs = AsyncMock(spec=GroupService)
    g1 = make_group(telegram_group_id=1)
    gs.find_suitable_groups_for_context_analysis = Mock(return_value=async_iter([g1]))

    uc = PeriodicContextAnalysisUseCase(group_service=gs, logger=_logger())
    await uc.execute()

    gs.process_group_context_analysis.assert_called_once_with(g1)


@pytest.mark.asyncio
async def test_periodic_context_analysis_continues_on_error():
    gs = AsyncMock(spec=GroupService)
    g1 = make_group(telegram_group_id=1)
    g2 = make_group(telegram_group_id=2)
    gs.find_suitable_groups_for_context_analysis = Mock(return_value=async_iter([g1, g2]))
    gs.process_group_context_analysis.side_effect = [Exception("error"), None]

    uc = PeriodicContextAnalysisUseCase(group_service=gs, logger=_logger())
    await uc.execute()

    assert gs.process_group_context_analysis.call_count == 2


# ---------------------------------------------------------------------------
# SetPersonaUseCase tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_persona_no_args_clears_persona():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, None)

    group_repo.set_persona.assert_called_once_with(1, None)
    assert "cleared" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_empty_string_clears_persona():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "   ")

    group_repo.set_persona.assert_called_once_with(1, None)
    assert "cleared" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_too_long():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "x" * (MAX_PERSONA_LENGTH + 1))

    group_repo.set_persona.assert_not_called()
    group_repo.find_by_tg_id.assert_not_called()
    assert str(MAX_PERSONA_LENGTH) in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_set_persona_exactly_max_chars_succeeds():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    persona = "x" * MAX_PERSONA_LENGTH

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, persona)

    group_repo.set_persona.assert_called_once_with(1, persona)
    assert "updated" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_strips_whitespace():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "  Funny and sarcastic  ")

    group_repo.set_persona.assert_called_once_with(1, "Funny and sarcastic")
    assert "updated" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "Funny and sarcastic")

    group_repo.set_persona.assert_not_called()
    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_success():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "Funny and sarcastic")

    group_repo.set_persona.assert_called_once_with(1, "Funny and sarcastic")
    assert "updated" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_persona_repo_exception():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(telegram_group_id=1)
    group_repo.find_by_tg_id.return_value = group
    group_repo.set_persona.side_effect = Exception("db error")

    uc = SetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123, "Funny")

    bot.send_message.assert_called_once()
    assert "Failed" in bot.send_message.call_args[0][1]


# ---------------------------------------------------------------------------
# GetPersonaUseCase tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_persona_group_not_found():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group_repo.find_by_tg_id.return_value = None

    uc = GetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)

    assert "not found" in bot.send_message.call_args[0][1].lower()


@pytest.mark.asyncio
async def test_get_persona_has_persona():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(persona="Witty and sarcastic")
    group_repo.find_by_tg_id.return_value = group

    uc = GetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)

    assert "Witty and sarcastic" in bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_get_persona_not_set():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    bot = AsyncMock(spec=TelegramBotPort)
    group = make_group(persona=None)
    group_repo.find_by_tg_id.return_value = group

    uc = GetPersonaUseCase(group_repo=group_repo, telegram_bot=bot, logger=_logger())
    await uc.execute(123)

    assert "No persona" in bot.send_message.call_args[0][1]
