import logging

from telegram.ext import Application
from dishka import AsyncContainer

from src.infrastructure.adapters.incoming.ptb_handlers import setup_handlers


logger = logging.getLogger(__name__)
_application: Application | None = None


def get_application() -> Application:
    if not _application:
        raise RuntimeError("PTB Application not initialized")
    return _application


async def start_polling_application(bot_token: str, container: AsyncContainer) -> None:
    global _application

    if _application:
        logger.warning("Application already initialized")
        return

    logger.info("Initializing PTB Application...")
    _application = Application.builder().token(bot_token).build()

    await _application.initialize()

    bot_user = await _application.bot.get_me()
    # Cache bot information
    _application.bot_data["bot_id"] = bot_user.id
    _application.bot_data["bot_username"] = bot_user.username
    _application.bot_data["container"] = container  # Cache container

    setup_handlers(_application)
    logger.info(f"Bot initialized: @{bot_user.username} (ID: {bot_user.id})")

    # Start bot polling
    await _application.start()
    await _application.updater.start_polling(drop_pending_updates=True)
    logger.info("Bot polling started")


async def shutdown_application() -> None:
    global _application

    if _application:
        logger.info("Shutting down PTB Application...")
        try:
            await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()
            logger.info("PTB Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during PTB Application shutdown: {e}", exc_info=True)
        finally:
            _application = None
