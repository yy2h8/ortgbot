import functools
import logging

from telegram import Update, ChatMember
from telegram.ext import ContextTypes

from src.domain.constants.bot_messages import NOT_GROUP_ADMIN


logger = logging.getLogger(__name__)


def only_in_group_chat(func):
    """Only handle updates coming to groups or supergroups."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat.type not in ["group", "supergroup"]:
            logger.debug(
                f"Ignoring non-group message from chat {update.effective_chat.id}"
            )
            return
        return await func(update, context)

    return wrapper


def only_for_group_admin(func):
    """Only handle updates if chat is a group and user is an admin."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat.type not in ["group", "supergroup"]:
            logger.debug(
                f"Ignoring non-group message from chat {update.effective_chat.id}"
            )
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except Exception as e:
            logger.error(f"Failed to check admin status: {e}")
            is_admin = False

        if not is_admin:
            await update.message.reply_text(NOT_GROUP_ADMIN)
            return

        return await func(update, context)

    return wrapper


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for all telegram errors."""
    logger.error(
        f"Exception while handling update {update}: {context.error}",
        exc_info=context.error,
    )
