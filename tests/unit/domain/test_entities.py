from datetime import datetime, timezone, timedelta

from src.domain.entities import Group, Message, GroupMember, GroupContext, GroupTrend, Request

from tests.conftest import make_group, make_message, make_group_member, make_group_context, make_group_trend, make_request


def test_create_group_auto_fills_is_active():
    group = make_group()
    assert group.is_active is True


def test_create_group_auto_fills_timestamps():
    before = datetime.now(timezone.utc)
    group = make_group()
    after = datetime.now(timezone.utc)
    assert before <= group.bot_added_at <= after
    assert before <= group.created_at <= after
    assert before <= group.updated_at <= after
    assert group.bot_added_at.tzinfo == timezone.utc
    assert group.created_at.tzinfo == timezone.utc
    assert group.updated_at.tzinfo == timezone.utc


def test_create_group_preserves_explicit_timestamps():
    ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    group = make_group(bot_added_at=ts, created_at=ts, updated_at=ts)
    assert group.bot_added_at == ts
    assert group.created_at == ts
    assert group.updated_at == ts


def test_create_request_auto_fills_created_at():
    before = datetime.now(timezone.utc)
    req = make_request()
    after = datetime.now(timezone.utc)
    assert before <= req.created_at <= after
    assert req.created_at.tzinfo == timezone.utc


def test_create_group_member_auto_fills_has_left_group():
    member = make_group_member()
    assert member.has_left_group is False


def test_create_group_member_auto_fills_timestamps():
    before = datetime.now(timezone.utc)
    member = make_group_member()
    after = datetime.now(timezone.utc)
    assert before <= member.created_at <= after
    assert before <= member.updated_at <= after
    assert member.created_at.tzinfo == timezone.utc
    assert member.updated_at.tzinfo == timezone.utc


def test_create_message_auto_fills_timestamps():
    before = datetime.now(timezone.utc)
    msg = make_message()
    after = datetime.now(timezone.utc)
    assert before <= msg.timestamp <= after
    assert before <= msg.created_at <= after
    assert msg.timestamp.tzinfo == timezone.utc
    assert msg.created_at.tzinfo == timezone.utc


def test_create_group_context_auto_fills_created_at():
    before = datetime.now(timezone.utc)
    ctx = make_group_context()
    after = datetime.now(timezone.utc)
    assert before <= ctx.created_at <= after
    assert ctx.created_at.tzinfo == timezone.utc


def test_create_group_trend_auto_fills_created_at():
    before = datetime.now(timezone.utc)
    trend = make_group_trend()
    after = datetime.now(timezone.utc)
    assert before <= trend.created_at <= after
    assert trend.created_at.tzinfo == timezone.utc


def test_create_group_with_explicit_optional_fields():
    ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    group = make_group(
        telegram_group_id=42,
        is_active=False,
        bot_added_at=ts,
        created_at=ts,
        updated_at=ts,
    )
    assert group.telegram_group_id == 42
    assert group.is_active is False
    assert group.bot_added_at == ts
    assert group.created_at == ts
    assert group.updated_at == ts


def test_create_message_with_explicit_optional_fields():
    ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    msg = make_message(
        timestamp=ts,
        created_at=ts,
        telegram_message_id=10,
        telegram_group_member_id=20,
        reply_to_message_id=30,
    )
    assert msg.timestamp == ts
    assert msg.created_at == ts
    assert msg.telegram_message_id == 10
    assert msg.telegram_group_member_id == 20
    assert msg.reply_to_message_id == 30


def test_create_group_member_with_explicit_optional_fields():
    ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    member = make_group_member(
        has_left_group=True,
        created_at=ts,
        updated_at=ts,
        telegram_group_member_id=50,
        username="testuser",
    )
    assert member.has_left_group is True
    assert member.created_at == ts
    assert member.updated_at == ts
    assert member.telegram_group_member_id == 50
    assert member.username == "testuser"
