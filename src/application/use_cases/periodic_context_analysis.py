import logging

from src.application.services.group_service import GroupService


class PeriodicContextAnalysisUseCase:
    def __init__(self, group_service: GroupService, logger: logging.Logger):
        self.group_service = group_service
        self.logger = logger

    async def execute(self) -> None:
        self.logger.info("Starting periodic context analysis across all groups")
        async for (
            group
        ) in self.group_service.find_suitable_groups_for_context_analysis():
            try:
                await self.group_service.process_group_context_analysis(group)
            except Exception as e:
                self.logger.error(
                    f"Error processing context analysis for group {group.telegram_group_id}: {e}"
                )
        self.logger.info("Completed periodic context analysis")
