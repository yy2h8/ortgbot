from typing import Sequence, Mapping, Dict

from src.domain.entities import Message
from src.domain.services.formatting import truncate_for_prompt


def format_conversation_for_prompt(
    messages: Sequence[Message],
) -> str:
    if not messages:
        return "[No messages in conversation]"

    visible_messages = [msg for msg in messages if msg.content and msg.content.strip()]

    if not visible_messages:
        return "[No messages in conversation]"

    user_mapping = _create_user_mapping(visible_messages)
    message_id_mapping = _create_message_id_mapping(visible_messages)
    message_lookup: Dict[int, Message] = {
        msg.telegram_message_id: msg for msg in visible_messages
    }

    formatted_lines = []
    for message in visible_messages:
        formatted_line = _format_single_message(
            message, user_mapping, message_id_mapping, message_lookup
        )
        formatted_lines.append(formatted_line)

    return "\n".join(formatted_lines)


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


def _create_message_id_mapping(messages: Sequence[Message]) -> Mapping[int, str]:
    """Create anonymized message ID mapping"""
    message_id_mapping: Dict[int, str] = {}
    for i, message in enumerate(messages, 1):
        message_id_mapping[message.telegram_message_id] = f"msg_{i}"

    return message_id_mapping


def build_conversation_messages(
    messages: Sequence[Message],
) -> list[dict[str, str]]:
    """Convert a sequence of Message entities into an OpenRouter messages array.

    Bot-generated messages become {"role": "assistant", "content": ...}.
    Human messages become {"role": "user", "content": "[user_N]: ..."}.
    Reply markers are preserved in the content string.
    Blank/None content is filtered out.
    Each content string is truncated via truncate_for_prompt().
    """
    visible_messages = [msg for msg in messages if msg.content and msg.content.strip()]

    if not visible_messages:
        return []

    user_mapping = _create_user_mapping(visible_messages)
    message_id_mapping = _create_message_id_mapping(visible_messages)
    message_lookup: Dict[int, Message] = {
        msg.telegram_message_id: msg for msg in visible_messages
    }

    result: list[dict[str, str]] = []
    for message in visible_messages:
        truncated_content = truncate_for_prompt(message.content)
        msg_id = message_id_mapping[message.telegram_message_id]

        if message.is_generated:
            role = "assistant"
            content = f"[{msg_id}] {truncated_content}"
        else:
            role = "user"
            speaker = user_mapping.get(
                message.telegram_group_member_id, "unknown_user"
            )
            if (
                bool(message.reply_to_message_id)
                and message.reply_to_message_id is not None
                and message.reply_to_message_id in message_lookup
            ):
                replied_message_id = message_id_mapping.get(
                    message.reply_to_message_id, "unknown"
                )
                content = (
                    f"[{msg_id}] [{speaker}] (replying to [{replied_message_id}]): "
                    f"{truncated_content}"
                )
            else:
                content = f"[{msg_id}] [{speaker}]: {truncated_content}"

        result.append({"role": role, "content": content})

    return result


def _format_single_message(
    message: Message,
    user_mapping: Mapping[int, str],
    message_id_mapping: Mapping[int, str],
    message_lookup: Mapping[int, Message],
) -> str:
    """Format a single message.

    Args:
        message: Message to format
        user_mapping: User ID to anonymized name mapping
        message_id_mapping: Message ID to anonymized ID mapping
        message_lookup: Telegram message ID to Message entity lookup

    Returns:
        Formatted message line with reply context if applicable
    """
    message_id = message_id_mapping[message.telegram_message_id]

    if message.is_generated:
        speaker = "you"
    else:
        speaker = user_mapping.get(message.telegram_group_member_id, "unknown_user")

    truncated_content = truncate_for_prompt(message.content)

    if (
        bool(message.reply_to_message_id)
        and message.reply_to_message_id is not None
        and message.reply_to_message_id in message_lookup
    ):
        replied_message_id = message_id_mapping.get(
            message.reply_to_message_id, "unknown"
        )
        return f"[{message_id}] {speaker} (replying to [{replied_message_id}]): {truncated_content}"
    else:
        return f"[{message_id}] {speaker}: {truncated_content}"
