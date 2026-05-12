import asyncio
import logging

from src.infrastructure.core.settings import load_settings
from src.infrastructure.core.logging import setup_logger, stop_logger
from src.infrastructure.core.dishka_lifecycle import (
    init_container,
    shutdown_container,
    get_container,
)
from src.infrastructure.core.ptb_lifecycle import (
    start_polling_application,
    shutdown_application,
)
from src.infrastructure.core.apscheduler_lifecycle import (
    start_scheduler,
    stop_scheduler,
)


async def main():
    try:
        settings = load_settings()
        setup_logger(settings)
        logger = logging.getLogger(__name__)

        logger.info("Initializing application resources...")
        container = await init_container(settings)
        await start_polling_application(settings.telegram_bot_token, container)
        start_scheduler()
        logger.info("Application resources initialized and started")

        # Keep running until interrupted
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down...")
        stop_scheduler(wait=False)
        await shutdown_application()
        await shutdown_container()
        logger.info("Resources cleaned up")
        stop_logger()


if __name__ == "__main__":
    asyncio.run(main())
