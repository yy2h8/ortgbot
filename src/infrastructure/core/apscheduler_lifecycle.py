import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.infrastructure.adapters.incoming.apscheduler_handlers import setup_handlers


logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler

    if _scheduler:
        logger.warning("Scheduler already initialized")
        return

    logger.info("Starting APScheduler for periodic tasks...")
    _scheduler = AsyncIOScheduler(timezone="UTC")
    setup_handlers(_scheduler)
    _scheduler.start()
    logger.info("APScheduler started successfully")


def stop_scheduler(wait: bool = False) -> None:
    """Shutdown the scheduler gracefully.

    Args:
        wait: If True, wait for running jobs to complete before shutdown
    """
    global _scheduler

    if _scheduler:
        logger.info("Shutting down APScheduler...")
        try:
            _scheduler.shutdown(wait=wait)
            logger.info("APScheduler stopped")
        except Exception as e:
            logger.error(f"Error during APScheduler shutdown: {e}", exc_info=True)
        finally:
            _scheduler = None
