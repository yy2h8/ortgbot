import logging

from dishka import make_async_container, AsyncContainer
from telegram.ext import Application

from src.infrastructure.core.settings import Settings
from src.infrastructure.core.database import AiosqliteDatabase
from src.infrastructure.core.dishka_providers import (
    InfrastructureProvider,
    RepositoryProvider,
    ServiceProvider,
    TelegramServiceProvider,
    UseCaseProvider,
)


logger = logging.getLogger(__name__)
_container: AsyncContainer | None = None


def get_container() -> AsyncContainer:
    if _container is None:
        raise RuntimeError("Container not initialized. Call init_container() first.")

    return _container


async def init_container(settings: Settings) -> AsyncContainer:
    global _container

    if _container:
        logger.warning("Container already initialized")
        return _container

    logger.info("Initializing dishka container...")
    _container = make_async_container(
        InfrastructureProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        TelegramServiceProvider(),
        UseCaseProvider(),
        context={Settings: settings},
    )

    # Initialize database schema
    database: AiosqliteDatabase = await _container.get(AiosqliteDatabase)
    await database.init_schema()
    logger.info(f"Database initialized at {settings.sqlite_db_path}")

    logger.info("Dishka container initialized successfully")
    return _container


async def shutdown_container() -> None:
    global _container

    if _container:
        logger.info("Shutting down dishka container...")
        try:
            await _container.close()
            logger.info("Dishka container shutdown complete")
        except Exception as e:
            logger.error(f"Error during dishka container shutdown: {e}", exc_info=True)
        finally:
            _container = None
