from typing import NamedTuple
from datetime import datetime


class TelegramMessage(NamedTuple):
    chat_tg_id: int
    chat_title: str
    user_tg_id: int
    user_first_name: str
    user_username: str | None
    user_is_bot: bool
    message_tg_id: int
    message_text: str
    reply_to_message_tg_id: int | None
    timestamp: datetime
    is_reply_to_bot_message: bool


class OpenRouterResponse(NamedTuple):
    content: str
    prompt_tokens: int
    completion_tokens: int
    raw_response: dict
    request_payload: dict
    cost: float


class Prompt(NamedTuple):
    system: str
    user: str
    temperature: float
    max_tokens: int


class ConversationPrompt(NamedTuple):
    system: str
    messages: list[dict[str, str]]
    temperature: float
    max_tokens: int
