import logging
import queue
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler

from src.infrastructure.core.settings import Settings

_log_listener: QueueListener | None = None


def setup_logger(settings: Settings) -> None:
    global _log_listener

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        settings.log_file,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    log_queue: queue.Queue = queue.Queue(-1)
    _log_listener = QueueListener(log_queue, file_handler, respect_handler_level=True)
    _log_listener.start()

    queue_handler = QueueHandler(log_queue)
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.addHandler(queue_handler)

    # logging.getLogger("httpx").setLevel(logging.WARNING)
    # logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    # logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


def stop_logger() -> None:
    global _log_listener
    if _log_listener is not None:
        _log_listener.stop()
        _log_listener = None
