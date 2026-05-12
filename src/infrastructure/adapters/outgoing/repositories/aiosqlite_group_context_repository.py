import logging
from datetime import datetime, timezone

from src.domain.entities import GroupContext
from src.application.ports.group_context_repository import GroupContextRepository
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteGroupContextRepository(GroupContextRepository):
    """SQLite adapter implementing GroupContextRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def create(self, group_context: GroupContext) -> GroupContext:
        self.logger.debug(
            f"Creating group context for group {group_context.telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    INSERT INTO ai_group_contexts
                    (telegram_group_id,
                     context_text, analysis_trends_count, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        group_context.telegram_group_id,
                        group_context.context_text,
                        group_context.analysis_trends_count,
                        int(group_context.created_at.timestamp()),
                    ),
                )
                await conn.commit()
                return group_context._replace(ai_group_context_id=cursor.lastrowid)
            except Exception as e:
                self.logger.error(f"Error creating group context: {e}")
                raise

    async def find_for_group(self, telegram_group_id: int) -> GroupContext | None:
        self.logger.debug(f"Finding group context for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT ai_group_context_id, telegram_group_id,
                       context_text, analysis_trends_count, created_at
                FROM ai_group_contexts
                WHERE telegram_group_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (telegram_group_id,),
            )
            row = await cursor.fetchone()

            return (
                GroupContext.create(
                    ai_group_context_id=row["ai_group_context_id"],
                    telegram_group_id=row["telegram_group_id"],
                    context_text=row["context_text"],
                    analysis_trends_count=row["analysis_trends_count"],
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def delete_old_contexts(self, telegram_group_id: int) -> None:
        self.logger.debug(f"Deleting old contexts for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    DELETE FROM ai_group_contexts
                    WHERE telegram_group_id = ?
                    """,
                    (telegram_group_id,),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error deleting old contexts for group {telegram_group_id}: {e}"
                )
                raise

    async def find_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, GroupContext]:
        self.logger.debug(f"Finding group context for {len(telegram_group_ids)} groups")
        placeholders = ",".join("?" * len(telegram_group_ids))
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT ai_group_context_id, telegram_group_id,
                       context_text, analysis_trends_count, created_at
                FROM ai_group_contexts c
                WHERE telegram_group_id IN ({placeholders})
                  AND ai_group_context_id = (
                      SELECT MAX(ai_group_context_id)
                      FROM ai_group_contexts
                      WHERE telegram_group_id = c.telegram_group_id
                  )
                """,
                telegram_group_ids,
            )
            rows = await cursor.fetchall()
            return {
                row["telegram_group_id"]: GroupContext.create(
                    ai_group_context_id=row["ai_group_context_id"],
                    telegram_group_id=row["telegram_group_id"],
                    context_text=row["context_text"],
                    analysis_trends_count=row["analysis_trends_count"],
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            }
