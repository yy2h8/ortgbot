import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.application.use_cases.periodic_trends_analysis import (
    PeriodicTrendsAnalysisUseCase,
)
from src.application.use_cases.periodic_context_analysis import (
    PeriodicContextAnalysisUseCase,
)
from src.application.ports.rate_limiter import RateLimiter
from src.infrastructure.adapters.outgoing.database_cleanup import DatabaseCleanup


logger = logging.getLogger(__name__)


async def _run_trends_analysis() -> None:
    from src.infrastructure.core.dishka_lifecycle import get_container

    container = get_container()
    use_case = await container.get(PeriodicTrendsAnalysisUseCase)

    try:
        await use_case.execute()
    except Exception as e:
        logger.error(f"PeriodicTrendsAnalysis use case failed: {e}", exc_info=True)


async def _run_context_analysis() -> None:
    from src.infrastructure.core.dishka_lifecycle import get_container

    container = get_container()
    use_case = await container.get(PeriodicContextAnalysisUseCase)

    try:
        await use_case.execute()
    except Exception as e:
        logger.error(f"PeriodicContextAnalysis use case failed: {e}", exc_info=True)


async def _cleanup_rate_limiter() -> None:
    from src.infrastructure.core.dishka_lifecycle import get_container

    container = get_container()
    rate_limiter = await container.get(RateLimiter)

    try:
        logger.info("Running rate limiter cleanup...")
        await rate_limiter.cleanup_expired_entries()
        logger.info("Rate limiter cleanup completed")
    except Exception as e:
        logger.error(f"Rate limiter cleanup failed: {e}", exc_info=True)


async def _run_database_cleanup() -> None:
    from src.infrastructure.core.dishka_lifecycle import get_container

    container = get_container()
    cleanup = await container.get(DatabaseCleanup)

    try:
        logger.info("Running database cleanup...")
        deleted_groups, deleted_members = await cleanup.cleanup()
        logger.info(
            f"Database cleanup completed: {deleted_groups} groups, {deleted_members} members removed"
        )
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}", exc_info=True)


def setup_handlers(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        _run_trends_analysis,
        CronTrigger(minute="0,15,30,45"),
        id="periodic_trends_analysis",
        name="Periodic Trends Analysis",
        replace_existing=True,
        misfire_grace_time=300,  # Allow 5 minutes grace for missed executions
    )
    logger.info("Scheduled periodic trends analysis (every 15 minutes)")

    scheduler.add_job(
        _run_context_analysis,
        CronTrigger(minute="0,30"),
        id="periodic_context_analysis",
        name="Periodic Context Analysis",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled periodic context analysis (every 30 minutes)")

    scheduler.add_job(
        _cleanup_rate_limiter,
        CronTrigger(minute="0,30"),
        id="rate_limiter_cleanup",
        name="Rate Limiter Cleanup",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled rate limiter cleanup (every 30 minutes)")

    scheduler.add_job(
        _run_database_cleanup,
        CronTrigger(hour=3, minute=0),
        id="database_cleanup",
        name="Database Cleanup",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled database cleanup (daily at 3 AM UTC)")
