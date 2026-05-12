import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    filters as Filters,
)

from src.infrastructure.core.ptb_util import (
    only_in_group_chat,
    only_for_group_admin,
    error_handler,
)

from src.domain.dto import TelegramMessage
from src.application.use_cases.chat_message import ChatMessageUseCase
from src.application.use_cases.member_left_group import MemberLeftGroupUseCase
from src.application.use_cases.group_joined import GroupJoinedUseCase
from src.application.use_cases.bot_left_group import BotLeftGroupUseCase
from src.application.use_cases.set_trigger_word import SetTriggerWordUseCase
from src.application.use_cases.set_language import SetLanguageUseCase
from src.application.use_cases.get_trigger_word import GetTriggerWordUseCase
from src.application.use_cases.get_language import GetLanguageUseCase
from src.application.use_cases.set_persona import SetPersonaUseCase
from src.application.use_cases.get_persona import GetPersonaUseCase
from src.infrastructure.adapters.outgoing.health_check import get_health


logger = logging.getLogger(__name__)


async def on_chat_member_updated(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle chat member status changes (members leaving)."""
    if not update.chat_member:
        return

    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status

    if old_status == "member" and new_status in ["left", "kicked"]:
        container = context.bot_data["container"]
        use_case: MemberLeftGroupUseCase = await container.get(MemberLeftGroupUseCase)

        try:
            await use_case.execute(
                update.effective_chat.id, update.chat_member.old_chat_member.user.id
            )
        except Exception as e:
            logger.error(f"MemberLeftGroup use case failed: {e}", exc_info=True)


async def on_my_chat_member_updated(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle bot being added/removed from groups."""
    if not update.my_chat_member:
        return

    old_status = update.my_chat_member.old_chat_member.status
    new_status = update.my_chat_member.new_chat_member.status
    container = context.bot_data["container"]

    # Bot was added to group
    if old_status in ["left", "kicked"] and new_status == "member":
        bot_username = context.bot_data["bot_username"]
        use_case: GroupJoinedUseCase = await container.get(GroupJoinedUseCase)
        logger.info(f"Bot joined new group: {update.effective_chat.id}")
        try:
            await use_case.execute(
                update.effective_chat.id, update.effective_chat.title, bot_username
            )
        except Exception as e:
            logger.error(f"GroupJoined use case failed: {e}", exc_info=True)

    # Bot was removed from group
    elif old_status == "member" and new_status in ["left", "kicked"]:
        use_case: BotLeftGroupUseCase = await container.get(BotLeftGroupUseCase)
        logger.info(f"Bot was removed from group: {update.effective_chat.id}")
        try:
            await use_case.execute(update.effective_chat.id)
        except Exception as e:
            logger.error(f"BotLeftGroup use case failed: {e}", exc_info=True)


@only_in_group_chat
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        logger.debug("Ignoring non-text message")
        return

    # Get container and cached bot ID
    container = context.bot_data["container"]
    bot_id = context.bot_data["bot_id"]
    bot_username = context.bot_data["bot_username"]
    use_case: ChatMessageUseCase = await container.get(ChatMessageUseCase)

    # Build DTO
    logger.info(f"Received chat message: {update.message.message_id}")
    dto = TelegramMessage(
        chat_tg_id=update.effective_chat.id,
        chat_title=update.effective_chat.title,
        user_tg_id=update.effective_user.id,
        user_first_name=update.effective_user.first_name,
        user_username=update.effective_user.username,
        user_is_bot=update.effective_user.is_bot,
        message_tg_id=update.message.message_id,
        message_text=update.message.text,
        reply_to_message_tg_id=(
            update.message.reply_to_message.message_id
            if update.message.reply_to_message
            else None
        ),
        timestamp=update.message.date,
        is_reply_to_bot_message=(
            update.message.reply_to_message.from_user.id == bot_id
            if update.message.reply_to_message
            else False
        ),
    )

    try:
        await use_case.execute(dto, bot_username)
    except Exception as e:
        logger.error(f"ChatMessage use case failed: {e}", exc_info=True)


@only_for_group_admin
async def handle_settrigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    container = context.bot_data["container"]
    bot_username = context.bot_data["bot_username"]
    use_case: SetTriggerWordUseCase = await container.get(SetTriggerWordUseCase)
    trigger_word = " ".join(context.args).strip()
    try:
        await use_case.execute(update.effective_chat.id, trigger_word, bot_username)
    except Exception as e:
        logger.error(f"SetTriggerWord use case failed: {e}", exc_info=True)


@only_in_group_chat
async def handle_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    container = context.bot_data["container"]
    use_case: GetTriggerWordUseCase = await container.get(GetTriggerWordUseCase)
    try:
        await use_case.execute(update.effective_chat.id)
    except Exception as e:
        logger.error(f"GetTriggerWord use case failed: {e}", exc_info=True)


@only_for_group_admin
async def handle_setlanguage(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    container = context.bot_data["container"]
    bot_username = context.bot_data["bot_username"]
    use_case: SetLanguageUseCase = await container.get(SetLanguageUseCase)
    language = " ".join(context.args).strip()
    try:
        await use_case.execute(update.effective_chat.id, language, bot_username)
    except Exception as e:
        logger.error(f"SetLanguage use case failed: {e}", exc_info=True)


@only_in_group_chat
async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    container = context.bot_data["container"]
    use_case: GetLanguageUseCase = await container.get(GetLanguageUseCase)
    try:
        await use_case.execute(update.effective_chat.id)
    except Exception as e:
        logger.error(f"GetLanguage use case failed: {e}", exc_info=True)


@only_for_group_admin
async def handle_setpersona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    container = context.bot_data["container"]
    use_case: SetPersonaUseCase = await container.get(SetPersonaUseCase)
    persona = " ".join(context.args).strip() if context.args else None
    try:
        await use_case.execute(update.effective_chat.id, persona)
    except Exception as e:
        logger.error(f"SetPersona use case failed: {e}", exc_info=True)


@only_in_group_chat
async def handle_persona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    container = context.bot_data["container"]
    use_case: GetPersonaUseCase = await container.get(GetPersonaUseCase)
    try:
        await use_case.execute(update.effective_chat.id)
    except Exception as e:
        logger.error(f"GetPersona use case failed: {e}", exc_info=True)


@only_for_group_admin
async def handle_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        report = await asyncio.to_thread(get_health)
        await update.message.reply_text(report)
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)


def setup_handlers(application: Application) -> None:
    """Register all Telegram handlers with the application.

    Handler order matters:
    1. Command handlers (specific commands)
    2. Chat member handlers (specific events)
    3. Message handlers (catch-all for text messages)
    4. Error handler (must be last)

    Args:
        application: PTB Application instance
    """
    logger.info("Registering Telegram handlers...")

    # Command handlers (must be before message handlers)
    application.add_handler(CommandHandler("settrigger", handle_settrigger))
    application.add_handler(CommandHandler("trigger", handle_trigger))
    application.add_handler(CommandHandler("setlanguage", handle_setlanguage))
    application.add_handler(CommandHandler("language", handle_language))
    application.add_handler(CommandHandler("setpersona", handle_setpersona))
    application.add_handler(CommandHandler("persona", handle_persona))
    application.add_handler(CommandHandler("health", handle_health))

    # Chat member status changes (members leaving)
    application.add_handler(
        ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER)
    )

    # Bot status changes (bot added/removed from groups)
    application.add_handler(
        ChatMemberHandler(on_my_chat_member_updated, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Message handler for group messages (should be last to catch all messages)
    application.add_handler(
        MessageHandler(Filters.ChatType.GROUPS & Filters.TEXT, handle_message)
    )

    # Global error handler (MUST be last)
    application.add_error_handler(error_handler)

    logger.info("Telegram handlers registered successfully")
