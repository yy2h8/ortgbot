from datetime import datetime, timezone

from src.domain.services.conversation_formatting import build_conversation_messages
from src.domain.constants.defaults import PROMPT_MESSAGE_MAX_LENGTH
from tests.conftest import make_message


def test_build_conversation_messages_empty_list():
    assert build_conversation_messages([]) == []


def test_build_conversation_messages_single_human_message():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="hello",
    )
    result = build_conversation_messages([msg])
    assert result == [{"role": "user", "content": "user_1 (16:34): hello"}]


def test_build_conversation_messages_bot_message_is_assistant_bare_text():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=None,
        is_generated=True,
        content="hi there",
    )
    result = build_conversation_messages([msg])
    assert result == [{"role": "assistant", "content": "hi there"}]


def test_build_conversation_messages_no_reply_annotation():
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
    result = build_conversation_messages([msg1, msg2])
    assert "replying to" not in result[1]["content"]
    assert result[1] == {"role": "user", "content": "user_2 (16:34): reply"}


def test_build_conversation_messages_blank_content_filtered():
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
    result = build_conversation_messages([msg1, msg2])
    assert len(result) == 1
    assert result[0] == {"role": "user", "content": "user_1 (16:34): visible"}


def test_build_conversation_messages_truncates_long_content():
    long_content = "a" * (PROMPT_MESSAGE_MAX_LENGTH + 50)
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content=long_content,
    )
    result = build_conversation_messages([msg])
    assert result[0]["content"].endswith("...")


def test_build_conversation_messages_all_human_returns_user_roles():
    msgs = [
        make_message(
            telegram_message_id=i,
            telegram_group_member_id=10,
            is_generated=False,
            content=f"msg{i}",
        )
        for i in range(1, 4)
    ]
    result = build_conversation_messages(msgs)
    assert len(result) == 3
    assert all(entry["role"] == "user" for entry in result)


def test_build_conversation_messages_mixed_roles_order():
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
    result = build_conversation_messages(msgs)
    assert [entry["role"] for entry in result] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert result[0]["content"] == "user_1 (16:34): hello"
    assert result[1]["content"] == "hi there"
    assert result[2]["content"] == "user_2 (16:34): how are you"
    assert result[3]["content"] == "doing great"


def test_build_conversation_messages_human_no_member_id_shows_unknown_user():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=None,
        is_generated=False,
        content="hello",
    )
    result = build_conversation_messages([msg])
    assert result[0] == {"role": "user", "content": "unknown_user (16:34): hello"}


def test_build_conversation_messages_all_whitespace_returns_empty():
    msgs = [
        make_message(telegram_message_id=1, telegram_group_member_id=10, content="   "),
        make_message(telegram_message_id=2, telegram_group_member_id=10, content="\t\n"),
    ]
    assert build_conversation_messages(msgs) == []


def test_build_conversation_messages_timestamp_in_content():
    msg = make_message(
        telegram_message_id=1,
        telegram_group_member_id=10,
        is_generated=False,
        content="hello",
        timestamp=datetime(2024, 6, 15, 9, 5, tzinfo=timezone.utc),
    )
    result = build_conversation_messages([msg])
    assert result[0]["content"] == "user_1 (09:05): hello"
