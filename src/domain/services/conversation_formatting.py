from typing import Sequence, Mapping, Dict

from src.domain.entities import Message
from src.domain.services.formatting import truncate_for_prompt


def _create_user_mapping(messages: Sequence[Message]) -> Mapping[int, str]:
    """Create anonymized user ID mapping"""
    unique_user_ids = set(
        msg.telegram_group_member_id for msg in messages if msg.telegram_group_member_id
    )

    anonymized_users: Dict[int, str] = {}
    for i, user_id in enumerate(sorted(unique_user_ids), 1):
        if user_id:  # Skip None values
            anonymized_users[user_id] = f"user_{i}"

    return anonymized_users


def build_conversation_messages(
    messages: Sequence[Message],
) -> list[dict[str, str]]:
    """Convert a sequence of Message entities into an OpenRouter messages array.

    Bot-generated messages become {"role": "assistant", "content": <bare text>}.
    Human messages become {"role": "user", "content": "user_N (HH:MM): <text>"}.
    Blank/None content is filtered out.
    Each content string is truncated via truncate_for_prompt().
    """
    visible_messages = [msg for msg in messages if msg.content and msg.content.strip()]

    if not visible_messages:
        return []

    user_mapping = _create_user_mapping(visible_messages)

    result: list[dict[str, str]] = []
    for message in visible_messages:
        truncated_content = truncate_for_prompt(message.content)

        if message.is_generated:
            result.append({"role": "assistant", "content": truncated_content})
        else:
            speaker = user_mapping.get(message.telegram_group_member_id, "unknown_user")
            timestamp = message.timestamp.strftime("%H:%M")
            result.append({"role": "user", "content": f"{speaker} ({timestamp}): {truncated_content}"})

    return result
