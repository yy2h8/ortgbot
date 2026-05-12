from datetime import datetime, timezone

from src.domain.services.conversation_formatting import format_conversation_for_prompt
from src.domain.constants.defaults import PROMPT_MESSAGE_MAX_LENGTH
from tests.conftest import make_message


def test_format_conversation_empty_list():
    assert format_conversation_for_prompt([]) == "[No messages in conversation]"


def test_format_conversation_single_human_message():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="hello",
    )
    result = format_conversation_for_prompt([msg])
    assert "[msg_1] user_1: hello" == result


def test_format_conversation_single_bot_message():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=None,
        is_generated=True,
        content="hi there",
    )
    result = format_conversation_for_prompt([msg])
    assert "[msg_1] you: hi there" == result


def test_format_conversation_two_different_users():
    msg1 = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="hello",
    )
    msg2 = make_message(
        telegram_message_id=2,
        telegram_group_member_id=20,
        is_generated=False,
        content="world",
    )
    result = format_conversation_for_prompt([msg1, msg2])
    assert "user_1" in result
    assert "user_2" in result


def test_format_conversation_reply_to_existing_message():
    msg1 = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="original",
    )
    msg2 = make_message(
        telegram_message_id=2,
        telegram_group_member_id=20,
        is_generated=False,
        content="reply",
        reply_to_message_id=1,
    )
    result = format_conversation_for_prompt([msg1, msg2])
    assert "(replying to [msg_1])" in result


def test_format_conversation_reply_to_unknown_message():
    msg = make_message(
        telegram_message_id=2,
        telegram_group_member_id=10,
        is_generated=False,
        content="reply",
        reply_to_message_id=999,
    )
    result = format_conversation_for_prompt([msg])
    assert "replying to" not in result


def test_format_conversation_empty_content_skipped():
    msg1 = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="",
    )
    msg2 = make_message(
        telegram_message_id=2,
        telegram_group_member_id=10,
        is_generated=False,
        content="visible",
    )
    result = format_conversation_for_prompt([msg1, msg2])
    lines = result.split("\n")
    assert len(lines) == 1
    assert "[msg_1] user_1: visible" == result


def test_format_conversation_long_message_truncated():
    long_content = "a" * (PROMPT_MESSAGE_MAX_LENGTH + 50)
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content=long_content,
    )
    result = format_conversation_for_prompt([msg])
    assert result.endswith("...")


def test_format_conversation_same_user_multiple_messages():
    msgs = [
        make_message(
            telegram_message_id=i,
            telegram_group_member_id=10,
            is_generated=False,
            content=f"msg{i}",
        )
        for i in range(1, 4)
    ]
    result = format_conversation_for_prompt(msgs)
    lines = result.split("\n")
    assert all("user_1" in line for line in lines)


def test_format_conversation_all_whitespace_returns_placeholder():
    msgs = [
        make_message(telegram_message_id=1, telegram_group_member_id=10, content="   "),
        make_message(telegram_message_id=2, telegram_group_member_id=10, content="\t\n"),
    ]
    assert format_conversation_for_prompt(msgs) == "[No messages in conversation]"


def test_format_conversation_reply_to_filtered_message_suppresses_context():
    msg1 = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        content="",
    )
    msg2 = make_message(
        telegram_message_id=2,
        telegram_group_member_id=20,
        content="reply",
        reply_to_message_id=1,
    )
    result = format_conversation_for_prompt([msg1, msg2])
    assert "replying to" not in result
    assert "[msg_1] user_1: reply" == result


def test_format_conversation_whitespace_only_skipped():
    msg1 = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        content="   ",
    )
    msg2 = make_message(
        telegram_message_id=2,
        telegram_group_member_id=10,
        content="visible",
    )
    result = format_conversation_for_prompt([msg1, msg2])
    lines = result.split("\n")
    assert len(lines) == 1
    assert "[msg_1] user_1: visible" == result


def test_format_conversation_human_no_member_id_shows_unknown_user():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=None,
        is_generated=False,
        content="hello",
    )
    result = format_conversation_for_prompt([msg])
    assert "[msg_1] unknown_user: hello" == result


def test_format_conversation_mixed_bot_and_human():
    msgs = [
        make_message(
            telegram_message_id=1,
            telegram_group_member_id=10,
            is_generated=False,
            content="hello",
        ),
        make_message(
            telegram_message_id=2,
            telegram_group_member_id=None,
            is_generated=True,
            content="hi there",
        ),
        make_message(
            telegram_message_id=3,
            telegram_group_member_id=20,
            is_generated=False,
            content="how are you",
        ),
        make_message(
            telegram_message_id=4,
            telegram_group_member_id=None,
            is_generated=True,
            content="doing great",
        ),
    ]
    result = format_conversation_for_prompt(msgs)
    lines = result.split("\n")
    assert len(lines) == 4
    assert "[msg_1] user_1: hello" == lines[0]
    assert "[msg_2] you: hi there" == lines[1]
    assert "[msg_3] user_2: how are you" == lines[2]
    assert "[msg_4] you: doing great" == lines[3]


def test_format_conversation_bot_replying_to_human():
    msgs = [
        make_message(
            telegram_message_id=1,
            telegram_group_member_id=10,
            is_generated=False,
            content="question",
        ),
        make_message(
            telegram_message_id=2,
            telegram_group_member_id=None,
            is_generated=True,
            content="answer",
            reply_to_message_id=1,
        ),
    ]
    result = format_conversation_for_prompt(msgs)
    lines = result.split("\n")
    assert len(lines) == 2
    assert "[msg_1] user_1: question" == lines[0]
    assert "[msg_2] you (replying to [msg_1]): answer" == lines[1]


def test_format_conversation_human_replying_to_bot():
    msgs = [
        make_message(
            telegram_message_id=1,
            telegram_group_member_id=None,
            is_generated=True,
            content="bot message",
        ),
        make_message(
            telegram_message_id=2,
            telegram_group_member_id=10,
            is_generated=False,
            content="human reply",
            reply_to_message_id=1,
        ),
    ]
    result = format_conversation_for_prompt(msgs)
    lines = result.split("\n")
    assert len(lines) == 2
    assert "[msg_1] you: bot message" == lines[0]
    assert "[msg_2] user_1 (replying to [msg_1]): human reply" == lines[1]
