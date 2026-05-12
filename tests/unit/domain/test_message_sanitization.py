from src.domain.services.message_sanitization import sanitize_for_ai_prompt


def test_sanitize_none_input():
    assert sanitize_for_ai_prompt(None, "bot") == ""


def test_sanitize_empty_string():
    assert sanitize_for_ai_prompt("", "bot") == ""


def test_sanitize_clean_text():
    assert sanitize_for_ai_prompt("hello world", "bot") == "hello world"


def test_sanitize_email_replacement():
    result = sanitize_for_ai_prompt("contact user@example.com please", "bot")
    assert result == "contact [EMAIL] please"


def test_sanitize_phone_replacement():
    result = sanitize_for_ai_prompt("call +12345678901 now", "bot")
    assert result == "call [PHONE] now"


def test_sanitize_phone_replacement_international():
    result = sanitize_for_ai_prompt("call +71234567890 now", "bot")
    assert result == "call [PHONE] now"


def test_sanitize_url_replacement():
    result = sanitize_for_ai_prompt("visit https://example.com/page", "bot")
    assert result == "visit [URL]"


def test_sanitize_bot_mention_removal():
    result = sanitize_for_ai_prompt("@mybot hello", "bot")
    assert result == "hello"


def test_sanitize_trigger_word_removal_case_insensitive():
    result = sanitize_for_ai_prompt("hey trigger hello", "trigger")
    assert result == "hey hello"


def test_sanitize_trigger_word_boundary_respected():
    result = sanitize_for_ai_prompt("triggering something", "trigger")
    assert result == "triggering something"


def test_sanitize_user_mention_replacement():
    result = sanitize_for_ai_prompt("@john hey", "bot")
    assert result == "[MENTION] hey"


def test_sanitize_multiple_whitespace_collapse():
    result = sanitize_for_ai_prompt("hello   world  foo", "bot")
    assert result == "hello world foo"


def test_sanitize_control_characters_stripped():
    result = sanitize_for_ai_prompt("hello\x00world", "bot")
    assert result == "helloworld"


def test_sanitize_newlines_and_tabs_collapsed():
    result = sanitize_for_ai_prompt("hello\nworld\tfoo", "bot")
    assert result == "hello world foo"


def test_sanitize_combined():
    text = "email user@test.com and visit https://site.com and @user hey trigger word"
    result = sanitize_for_ai_prompt(text, "trigger")
    assert "[EMAIL]" in result
    assert "[URL]" in result
    assert "[MENTION]" in result
    assert "trigger" not in result.split()


def test_sanitize_bot_mention_not_eating_user_mentions():
    result = sanitize_for_ai_prompt("@somebot @user", "bot")
    assert "[MENTION]" in result
    assert "somebot" not in result


def test_sanitize_empty_trigger_word_safe():
    result = sanitize_for_ai_prompt("hello world", "")
    assert result == "hello world"


def test_sanitize_trigger_word_regex_special_chars_dot():
    result = sanitize_for_ai_prompt("say hello.world now", "hello.world")
    assert result == "say now"


def test_sanitize_trigger_word_regex_special_chars_pipe():
    result = sanitize_for_ai_prompt("match foo|bar here", "foo|bar")
    assert result == "match here"


def test_sanitize_phone_six_digits_not_replaced():
    result = sanitize_for_ai_prompt("number 123456 end", "bot")
    assert result == "number 123456 end"


def test_sanitize_phone_seven_digits_replaced():
    result = sanitize_for_ai_prompt("number 1234567 end", "bot")
    assert result == "number [PHONE] end"


def test_sanitize_phone_fifteen_digits_replaced():
    result = sanitize_for_ai_prompt("number +123456789012345 end", "bot")
    assert result == "number [PHONE] end"


def test_sanitize_phone_sixteen_digits_not_replaced():
    result = sanitize_for_ai_prompt("number 1234567890123456 end", "bot")
    assert result == "number 1234567890123456 end"


def test_sanitize_whitespace_only_returns_empty():
    assert sanitize_for_ai_prompt("   \t\n  ", "bot") == ""


def test_sanitize_becomes_empty_after_bot_mention_removal():
    assert sanitize_for_ai_prompt("@mybot", "bot") == ""


def test_sanitize_becomes_empty_after_trigger_word_removal():
    assert sanitize_for_ai_prompt("trigger", "trigger") == ""


def test_sanitize_url_ftp_scheme():
    result = sanitize_for_ai_prompt("download ftp://files.example.com/doc", "bot")
    assert result == "download [URL]"


def test_sanitize_url_www_scheme():
    result = sanitize_for_ai_prompt("visit www.example.com/page", "bot")
    assert result == "visit [URL]"
