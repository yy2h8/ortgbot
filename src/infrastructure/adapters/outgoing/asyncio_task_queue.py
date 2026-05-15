import asyncio
import logging

from src.application.ports.task_queue import TaskQueue
from src.application.use_cases.reply_to_message import ReplyToMessageUseCase
from src.application.use_cases.follow_up_message import FollowUpMessageUseCase


class AsyncioTaskQueue(TaskQueue):
    """Task queue implementation using asyncio.create_task"""

    MAX_CONCURRENT_TASKS: int = 5

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)

    def queue_reply_to_message(
        self, telegram_message_id: int, randomly_selected: bool = False
    ) -> None:
        asyncio.create_task(
            self._reply_to_message_async(telegram_message_id, randomly_selected)
        )

    def queue_follow_up(self, telegram_message_id: int, delay: float) -> None:
        asyncio.create_task(self._follow_up_with_delay(telegram_message_id, delay))

    async def _reply_to_message_async(
        self, telegram_message_id: int, randomly_selected: bool
    ) -> None:
        """Background task wrapper for bot reply generation"""
        from src.infrastructure.core.dishka_lifecycle import get_container

        async with self._semaphore:
            try:
                container = get_container()
                use_case = await container.get(ReplyToMessageUseCase)
                await use_case.execute(telegram_message_id, randomly_selected)
            except Exception as e:
                self.logger.error(
                    f"Bot reply failed for message {telegram_message_id}: {e}",
                    exc_info=True,
                )

    async def _follow_up_with_delay(
        self, telegram_message_id: int, delay: float
    ) -> None:
        """Background task wrapper for follow-up message with delay"""
        from src.infrastructure.core.dishka_lifecycle import get_container

        await asyncio.sleep(delay)
        async with self._semaphore:
            try:
                container = get_container()
                use_case = await container.get(FollowUpMessageUseCase)
                await use_case.execute(telegram_message_id)
            except Exception as e:
                self.logger.error(
                    f"Follow-up message failed for message {telegram_message_id}: {e}",
                    exc_info=True,
                )
