import re
from datetime import datetime, timedelta, timezone

from src.domain.entities import GroupContext, GroupTrend, Group, Message
from src.domain.dto import TelegramMessage
from src.domain.constants.defaults import INITIAL_TRENDS_THRESHOLD


def evaluate_trends_suitability(
    group_message_count: int,
    latest_trend: GroupTrend | None,
    message_limit: int,
) -> bool:
    if latest_trend is None:
        if group_message_count >= INITIAL_TRENDS_THRESHOLD:
            # No previous trend, but enough messages to start analysis
            return True
        return False

    if latest_trend.analysis_message_count < message_limit:
        if group_message_count > latest_trend.analysis_message_count:
            # Latest trend incomplete, but enough new messages to continue analysis
            return True
        return False

    if group_message_count >= message_limit:
        return True

    return False


def evaluate_context_suitability(
    trends_count: int,
    previous_context: GroupContext | None,
    max_trends_for_context: int,
) -> bool:
    if previous_context is None:
        if trends_count > 1:
            return True
        return False

    if previous_context.analysis_trends_count < max_trends_for_context:
        if trends_count > previous_context.analysis_trends_count:
            # Incomplete previous context, but enough new trends to continue analysis
            return True
        return False

    if trends_count >= max_trends_for_context:
        return True

    return False


_USERNAME_PATTERNS: dict[str, re.Pattern] = {}
_TRIGGER_PATTERNS: dict[str, re.Pattern] = {}


def evaluate_reply_suitability(
    dto: TelegramMessage, group: Group, bot_username: str
) -> bool:
    if not dto.message_text:
        return False

    if dto.is_reply_to_bot_message:
        return True

    if bot_username not in _USERNAME_PATTERNS:
        _USERNAME_PATTERNS[bot_username] = re.compile(
            rf"(?<!\w)@{re.escape(bot_username)}\b", re.IGNORECASE
        )

    if _USERNAME_PATTERNS[bot_username].search(dto.message_text):
        return True

    if group.trigger_word not in _TRIGGER_PATTERNS:
        _TRIGGER_PATTERNS[group.trigger_word] = re.compile(
            rf"\b{re.escape(group.trigger_word)}\b", re.IGNORECASE
        )

    if _TRIGGER_PATTERNS[group.trigger_word].search(dto.message_text):
        return True

    return False
