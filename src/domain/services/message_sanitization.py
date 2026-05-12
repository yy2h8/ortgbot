import re
import unicodedata


_EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}"
    r"(?![\w.-])"
)
_PHONE_PATTERN = re.compile(
    r"(?<!\w)"
    r"(?:\+?\d[\d\s().-]{5,}\d)"
    r"(?!\w)"
)
_URL_PATTERN = re.compile(r"(?i)\b(?:https?://|ftp://|www\.)[^\s<>()]+")
_BOT_MENTION_PATTERN = re.compile(
    r"(?<!\w)@[A-Za-z0-9_]*bot\b",
    re.IGNORECASE,
)
_MENTION_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_]{1,32}\b")
_NON_DIGIT_PATTERN = re.compile(r"\D")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_TRIGGER_PATTERNS: dict[str, re.Pattern] = {}


def _replace_phone(match: re.Match[str]) -> str:
    value = match.group(0)
    digits = _NON_DIGIT_PATTERN.sub("", value)
    return "[PHONE]" if 7 <= len(digits) <= 15 else value


def sanitize_for_ai_prompt(text: str | None, trigger_word: str) -> str:
    if not text:
        return ""

    sanitized = unicodedata.normalize("NFKC", text).strip()

    sanitized = _EMAIL_PATTERN.sub("[EMAIL]", sanitized)
    sanitized = _PHONE_PATTERN.sub(_replace_phone, sanitized)
    sanitized = _URL_PATTERN.sub("[URL]", sanitized)
    sanitized = _BOT_MENTION_PATTERN.sub("", sanitized)

    if trigger_word:
        if trigger_word not in _TRIGGER_PATTERNS:
            _TRIGGER_PATTERNS[trigger_word] = re.compile(
                rf"\b{re.escape(trigger_word)}\b", re.IGNORECASE
            )
        sanitized = _TRIGGER_PATTERNS[trigger_word].sub("", sanitized)

    sanitized = _MENTION_PATTERN.sub("[MENTION]", sanitized)
    sanitized = _WHITESPACE_PATTERN.sub(" ", sanitized).strip()
    sanitized = _CONTROL_CHARS_PATTERN.sub("", sanitized)

    return sanitized.strip()
