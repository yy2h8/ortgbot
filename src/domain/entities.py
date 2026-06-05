from typing import NamedTuple, Any
from datetime import datetime, timezone


class GroupContext(NamedTuple):
    telegram_group_id: int
    context_text: str
    analysis_trends_count: int
    created_at: datetime
    ai_group_context_id: int | None

    @classmethod
    def create(
        cls,
        telegram_group_id: int,
        context_text: str,
        analysis_trends_count: int,
        created_at: datetime | None = None,
        ai_group_context_id: int | None = None,
    ) -> "GroupContext":
        """Factory method for creating a group context"""
        return cls(
            telegram_group_id=telegram_group_id,
            context_text=context_text,
            analysis_trends_count=analysis_trends_count,
            created_at=created_at or datetime.now(timezone.utc),
            ai_group_context_id=ai_group_context_id,
        )


class GroupTrend(NamedTuple):
    telegram_group_id: int
    recent_trends_text: str
    analysis_message_count: int
    created_at: datetime
    ai_group_trend_id: int | None

    @classmethod
    def create(
        cls,
        telegram_group_id: int,
        recent_trends_text: str,
        analysis_message_count: int,
        created_at: datetime | None = None,
        ai_group_trend_id: int | None = None,
    ) -> "GroupTrend":
        """Factory method for creating a group trend"""
        return cls(
            telegram_group_id=telegram_group_id,
            recent_trends_text=recent_trends_text,
            analysis_message_count=analysis_message_count,
            created_at=created_at or datetime.now(timezone.utc),
            ai_group_trend_id=ai_group_trend_id,
        )


class Request(NamedTuple):
    telegram_group_id: int
    created_at: datetime
    openrouter_request_id: int | None
    success: bool | None
    model_openrouter_id: str | None
    prompt_tokens_usage: int | None
    completion_tokens_usage: int | None
    cost_estimate_usd: float | None
    request_payload: dict[str, Any] | None
    response_content: dict[str, Any] | None
    error_message: str | None
    processing_time_ms: int | None

    @classmethod
    def create(
        cls,
        telegram_group_id: int,
        success: bool | None = None,
        model_openrouter_id: str | None = None,
        prompt_tokens_usage: int | None = None,
        completion_tokens_usage: int | None = None,
        cost_estimate_usd: float | None = None,
        request_payload: dict[str, Any] | None = None,
        response_content: dict[str, Any] | None = None,
        error_message: str | None = None,
        processing_time_ms: int | None = None,
    ) -> "Request":
        """Factory method for creating a new request"""
        return cls(
            telegram_group_id=telegram_group_id,
            created_at=datetime.now(timezone.utc),
            openrouter_request_id=None,
            success=success,
            model_openrouter_id=model_openrouter_id,
            prompt_tokens_usage=prompt_tokens_usage,
            completion_tokens_usage=completion_tokens_usage,
            cost_estimate_usd=cost_estimate_usd,
            request_payload=request_payload,
            response_content=response_content,
            error_message=error_message,
            processing_time_ms=processing_time_ms,
        )


class Group(NamedTuple):
    tg_id: int
    title: str
    language: str
    trigger_word: str
    telegram_group_id: int | None
    is_active: bool | None
    bot_added_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    persona: str | None

    @classmethod
    def create(
        cls,
        tg_id: int,
        title: str,
        language: str,
        trigger_word: str,
        telegram_group_id: int | None = None,
        is_active: bool | None = None,
        bot_added_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        persona: str | None = None,
    ) -> "Group":
        """Factory method for creating a group"""
        now = datetime.now(timezone.utc)
        return cls(
            tg_id=tg_id,
            title=title,
            language=language,
            trigger_word=trigger_word,
            telegram_group_id=telegram_group_id,
            is_active=is_active if is_active is not None else True,
            bot_added_at=bot_added_at or now,
            created_at=created_at or now,
            updated_at=updated_at or now,
            persona=persona,
        )


class GroupMember(NamedTuple):
    telegram_group_id: int
    tg_id: int
    first_name: str
    is_bot: bool
    has_left_group: bool
    created_at: datetime
    updated_at: datetime
    telegram_group_member_id: int | None
    username: str | None

    @classmethod
    def create(
        cls,
        telegram_group_id: int,
        tg_id: int,
        first_name: str,
        is_bot: bool | None = None,
        has_left_group: bool | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        telegram_group_member_id: int | None = None,
        username: str | None = None,
    ) -> "GroupMember":
        """Factory method for creating a group member"""
        now = datetime.now(timezone.utc)
        return cls(
            telegram_group_id=telegram_group_id,
            tg_id=tg_id,
            first_name=first_name,
            is_bot=is_bot if is_bot is not None else False,
            has_left_group=has_left_group if has_left_group is not None else False,
            created_at=created_at or now,
            updated_at=updated_at or now,
            telegram_group_member_id=telegram_group_member_id,
            username=username,
        )


class Message(NamedTuple):
    telegram_group_id: int
    tg_id: int
    content: str
    timestamp: datetime
    is_reply_to_bot_message: bool
    is_generated: bool
    created_at: datetime
    telegram_message_id: int | None
    telegram_group_member_id: int | None
    reply_to_message_id: int | None

    @classmethod
    def create(
        cls,
        telegram_group_id: int,
        tg_id: int,
        content: str,
        is_reply_to_bot_message: bool,
        is_generated: bool,
        timestamp: datetime | None = None,
        created_at: datetime | None = None,
        telegram_message_id: int | None = None,
        telegram_group_member_id: int | None = None,
        reply_to_message_id: int | None = None,
    ) -> "Message":
        """Factory method for creating a message"""
        now = datetime.now(timezone.utc)
        return cls(
            telegram_group_id=telegram_group_id,
            tg_id=tg_id,
            content=content,
            is_reply_to_bot_message=is_reply_to_bot_message,
            is_generated=is_generated,
            timestamp=timestamp or now,
            created_at=created_at or now,
            telegram_message_id=telegram_message_id,
            telegram_group_member_id=telegram_group_member_id,
            reply_to_message_id=reply_to_message_id,
        )
