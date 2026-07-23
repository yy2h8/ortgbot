from src.domain.services.formatting import (
    PROMPT_MESSAGE_MAX_LENGTH,
    format_trends_for_prompt,
    strip_message_id_prefix,
    strip_paired_quotes,
    truncate_for_prompt,
)
from tests.conftest import make_group_trend


# ---------------------------------------------------------------------------
# format_trends_for_prompt
# ---------------------------------------------------------------------------


def test_format_trends_empty_list():
    assert format_trends_for_prompt([]) == "[No trends available]"


def test_format_trends_single_trend_starts_with_trend_1():
    trend = make_group_trend(recent_trends_text="People are talking about cats")
    result = format_trends_for_prompt([trend])
    assert result.startswith("Trend 1:")


def test_format_trends_single_trend_contains_text():
    trend = make_group_trend(recent_trends_text="People are talking about cats")
    result = format_trends_for_prompt([trend])
    lines = result.splitlines()
    assert lines[0] == "Trend 1:"
    assert lines[1] == "People are talking about cats"


def test_format_trends_single_trend_no_separator():
    trend = make_group_trend(recent_trends_text="Some trend")
    result = format_trends_for_prompt([trend])
    assert "-" * 30 not in result


def test_format_trends_two_trends_separator_between():
    t1 = make_group_trend(recent_trends_text="Trend A text")
    t2 = make_group_trend(recent_trends_text="Trend B text")
    result = format_trends_for_prompt([t1, t2])
    assert "-" * 30 in result


def test_format_trends_two_trends_no_trailing_separator():
    t1 = make_group_trend(recent_trends_text="Trend A text")
    t2 = make_group_trend(recent_trends_text="Trend B text")
    result = format_trends_for_prompt([t1, t2])
    assert not result.endswith("-" * 30)


def test_format_trends_numbering_increments():
    trends = [make_group_trend(recent_trends_text=f"text {i}") for i in range(3)]
    result = format_trends_for_prompt(trends)
    assert "Trend 1:" in result
    assert "Trend 2:" in result
    assert "Trend 3:" in result


# ---------------------------------------------------------------------------
# strip_paired_quotes
# ---------------------------------------------------------------------------


def test_strip_paired_quotes_removes_outer():
    assert strip_paired_quotes('"hello"') == "hello"


def test_strip_paired_quotes_no_leading_quote():
    assert strip_paired_quotes('hello"') == 'hello"'


def test_strip_paired_quotes_no_trailing_quote():
    assert strip_paired_quotes('"hello') == '"hello'


def test_strip_paired_quotes_no_quotes():
    assert strip_paired_quotes("hello") == "hello"


def test_strip_paired_quotes_empty_string():
    assert strip_paired_quotes("") == ""


def test_strip_paired_quotes_single_char_quote():
    assert strip_paired_quotes('"') == '"'


def test_strip_paired_quotes_exactly_two_double_quotes():
    assert strip_paired_quotes('""') == ""


def test_strip_paired_quotes_strips_only_one_layer():
    assert strip_paired_quotes('""hello""') == '"hello"'


def test_strip_paired_quotes_single_quotes_unchanged():
    assert strip_paired_quotes("'hello'") == "'hello'"


# ---------------------------------------------------------------------------
# strip_message_id_prefix
# ---------------------------------------------------------------------------


def test_strip_message_id_prefix_removes_single_digit():
    assert strip_message_id_prefix("[msg_6] hello") == "hello"


def test_strip_message_id_prefix_removes_multi_digit():
    assert strip_message_id_prefix("[msg_42] hello") == "hello"


def test_strip_message_id_prefix_no_marker_unchanged():
    assert strip_message_id_prefix("just text") == "just text"


def test_strip_message_id_prefix_empty_string():
    assert strip_message_id_prefix("") == ""


def test_strip_message_id_prefix_only_marker():
    assert strip_message_id_prefix("[msg_1]") == ""


def test_strip_message_id_prefix_strips_leading_whitespace_after_marker():
    assert strip_message_id_prefix("[msg_2]   spaced") == "spaced"


def test_strip_message_id_prefix_marker_not_at_start_unchanged():
    assert strip_message_id_prefix("text [msg_1] more") == "text [msg_1] more"


def test_strip_message_id_prefix_non_numeric_inside_brackets_unchanged():
    assert strip_message_id_prefix("[user_1] hello") == "[user_1] hello"


# ---------------------------------------------------------------------------
# truncate_for_prompt
# ---------------------------------------------------------------------------



def test_truncate_below_limit_unchanged():
    text = "a" * (PROMPT_MESSAGE_MAX_LENGTH - 1)
    result = truncate_for_prompt(text)
    assert result == text
    assert not result.endswith("...")


def test_truncate_at_exact_limit_unchanged():
    text = "a" * PROMPT_MESSAGE_MAX_LENGTH
    result = truncate_for_prompt(text)
    assert result == text
    assert not result.endswith("...")


def test_truncate_one_over_limit():
    text = "a" * (PROMPT_MESSAGE_MAX_LENGTH + 1)
    result = truncate_for_prompt(text)
    assert result == "a" * PROMPT_MESSAGE_MAX_LENGTH + "..."


def test_truncate_well_above_limit():
    text = "b" * (PROMPT_MESSAGE_MAX_LENGTH + 50)
    result = truncate_for_prompt(text)
    assert result == "b" * PROMPT_MESSAGE_MAX_LENGTH + "..."


def test_truncate_empty_string():
    assert truncate_for_prompt("") == ""


def test_truncate_custom_max_length():
    text = "hello world!"
    result = truncate_for_prompt(text, max_length=10)
    assert result == "hello worl..."

