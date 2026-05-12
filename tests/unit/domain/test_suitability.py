from datetime import datetime, timedelta, timezone

from src.domain.services.suitability import (
    evaluate_trends_suitability,
    evaluate_context_suitability,
    evaluate_reply_suitability,
)
from src.domain.constants.defaults import INITIAL_TRENDS_THRESHOLD
from tests.conftest import (
    make_group,
    make_group_trend,
    make_group_context,
    make_message,
    make_telegram_message,
)


def test_evaluate_trends_no_trend_messages_below_threshold():
    assert evaluate_trends_suitability(INITIAL_TRENDS_THRESHOLD - 1, None, 50) is False


def test_evaluate_trends_no_trend_messages_at_threshold():
    assert evaluate_trends_suitability(INITIAL_TRENDS_THRESHOLD, None, 50) is True


def test_evaluate_trends_complete_group_has_enough():
    trend = make_group_trend(analysis_message_count=50)
    assert evaluate_trends_suitability(50, trend, 50) is True


def test_evaluate_trends_complete_group_under_limit():
    trend = make_group_trend(analysis_message_count=50)
    assert evaluate_trends_suitability(40, trend, 50) is False


def test_evaluate_trends_incomplete_new_msgs_available():
    trend = make_group_trend(analysis_message_count=30)
    assert evaluate_trends_suitability(45, trend, 50) is True


def test_evaluate_trends_incomplete_no_new_msgs():
    trend = make_group_trend(analysis_message_count=30)
    assert evaluate_trends_suitability(30, trend, 50) is False


def test_evaluate_trends_incomplete_exact_equality():
    trend = make_group_trend(analysis_message_count=30)
    assert evaluate_trends_suitability(30, trend, 50) is False


def test_evaluate_context_no_context_trends_le_1():
    assert evaluate_context_suitability(1, None, 5) is False


def test_evaluate_context_no_context_trends_gt_1():
    assert evaluate_context_suitability(2, None, 5) is True


def test_evaluate_context_no_context_trends_0():
    assert evaluate_context_suitability(0, None, 5) is False


def test_evaluate_context_complete_trends_ge_max():
    ctx = make_group_context(analysis_trends_count=5)
    assert evaluate_context_suitability(5, ctx, 5) is True


def test_evaluate_context_complete_trends_lt_max():
    ctx = make_group_context(analysis_trends_count=5)
    assert evaluate_context_suitability(3, ctx, 5) is False


def test_evaluate_context_incomplete_new_trends_available():
    ctx = make_group_context(analysis_trends_count=2)
    assert evaluate_context_suitability(4, ctx, 5) is True


def test_evaluate_context_incomplete_no_new_trends():
    ctx = make_group_context(analysis_trends_count=2)
    assert evaluate_context_suitability(2, ctx, 5) is False


def test_evaluate_context_incomplete_exact_equality():
    ctx = make_group_context(analysis_trends_count=3)
    assert evaluate_context_suitability(3, ctx, 5) is False


def test_evaluate_reply_empty_message_text():
    dto = make_telegram_message(message_text="")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is False


def test_evaluate_reply_to_bot_message():
    dto = make_telegram_message(is_reply_to_bot_message=True, message_text="hello")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_bot_mention():
    dto = make_telegram_message(message_text="hey @mybot")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_bot_mention_case_insensitive():
    dto = make_telegram_message(message_text="hey @MyBot")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_trigger_word():
    dto = make_telegram_message(message_text="hey trigger hello")
    group = make_group(trigger_word="trigger")
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_trigger_word_case_insensitive():
    dto = make_telegram_message(message_text="hey TRIGGER hello")
    group = make_group(trigger_word="trigger")
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_trigger_word_boundary():
    dto = make_telegram_message(message_text="triggering")
    group = make_group(trigger_word="trigger")
    assert evaluate_reply_suitability(dto, group, "mybot") is False


def test_evaluate_reply_no_match():
    dto = make_telegram_message(message_text="hello world")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is False


def test_evaluate_reply_bot_mention_no_preceding_boundary():
    dto = make_telegram_message(message_text="sometext@mybot")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is False


def test_evaluate_reply_whitespace_only():
    dto = make_telegram_message(message_text="   ")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is False


def test_evaluate_reply_trigger_word_only():
    dto = make_telegram_message(message_text="trigger")
    group = make_group(trigger_word="trigger")
    assert evaluate_reply_suitability(dto, group, "mybot") is True


def test_evaluate_reply_bot_mention_trailing_punctuation():
    dto = make_telegram_message(message_text="hey @mybot?")
    group = make_group()
    assert evaluate_reply_suitability(dto, group, "mybot") is True
