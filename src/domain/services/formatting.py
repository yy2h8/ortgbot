import re

from src.domain.entities import GroupTrend
from src.domain.constants.defaults import PROMPT_MESSAGE_MAX_LENGTH


_MESSAGE_ID_PREFIX_PATTERN = re.compile(r"^\[msg_\d+\]\s*")


def strip_paired_quotes(text: str) -> str:
    """Remove outer double quotes only if present at both start and end."""
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text


def strip_message_id_prefix(text: str) -> str:
    """Remove a leading message ID marker (e.g. "[msg_6]") that models may mimic
    from the conversation history format."""
    return _MESSAGE_ID_PREFIX_PATTERN.sub("", text)


def format_trends_for_prompt(trends: list[GroupTrend]) -> str:
    if not trends:
        return "[No trends available]"

    formatted_lines: list[str] = []

    for i, trend in enumerate(trends, 1):
        formatted_lines.append(f"Trend {i}:")
        formatted_lines.append(trend.recent_trends_text)

        if i < len(trends):
            formatted_lines.append("-" * 30)

    return "\n".join(formatted_lines)


def truncate_for_prompt(
    content: str, max_length: int = PROMPT_MESSAGE_MAX_LENGTH
) -> str:
    """Truncate text to the safe prompt length, adding ellipsis when needed."""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."
