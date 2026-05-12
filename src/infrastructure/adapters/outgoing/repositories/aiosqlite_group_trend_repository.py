import logging
from datetime import datetime, timezone

from src.domain.entities import GroupTrend
from src.application.ports.group_trend_repository import GroupTrendRepository
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteGroupTrendRepository(GroupTrendRepository):
    """SQLite adapter implementing GroupTrendRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def create(self, group_trend: GroupTrend) -> GroupTrend:
        self.logger.debug(
            f"Creating group trend for group {group_trend.telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    INSERT INTO ai_group_trends
                    (telegram_group_id,
                     recent_trends_text,
                     analysis_message_count, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        group_trend.telegram_group_id,
                        group_trend.recent_trends_text,
                        group_trend.analysis_message_count,
                        int(group_trend.created_at.timestamp()),
                    ),
                )
                await conn.commit()
                return group_trend._replace(ai_group_trend_id=cursor.lastrowid)
            except Exception as e:
                self.logger.error(f"Error creating group trend: {e}")
                raise

    async def find_latest_for_group(self, telegram_group_id: int) -> GroupTrend | None:
        self.logger.debug(f"Fetching latest trend for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT ai_group_trend_id, telegram_group_id,
                       recent_trends_text,
                       analysis_message_count, created_at
                FROM ai_group_trends
                WHERE telegram_group_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (telegram_group_id,),
            )
            row = await cursor.fetchone()

            return (
                GroupTrend.create(
                    ai_group_trend_id=row["ai_group_trend_id"],
                    telegram_group_id=row["telegram_group_id"],
                    recent_trends_text=row["recent_trends_text"],
                    analysis_message_count=row["analysis_message_count"],
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def delete_incomplete_trends(
        self, telegram_group_id: int, message_limit: int
    ) -> None:
        self.logger.info(f"Deleting incomplete trends for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    DELETE FROM ai_group_trends
                    WHERE telegram_group_id = ?
                    AND analysis_message_count < ?
                    """,
                    (telegram_group_id, message_limit),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error deleting incomplete trends for group {telegram_group_id}: {e}"
                )
                raise

    async def find_all_for_group(self, telegram_group_id: int) -> list[GroupTrend]:
        self.logger.debug(f"Fetching all trends for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT ai_group_trend_id, telegram_group_id,
                       recent_trends_text,
                       analysis_message_count, created_at
                FROM ai_group_trends
                WHERE telegram_group_id = ?
                ORDER BY created_at ASC
                """,
                (telegram_group_id,),
            )
            rows = await cursor.fetchall()
            return [
                GroupTrend.create(
                    ai_group_trend_id=row["ai_group_trend_id"],
                    telegram_group_id=row["telegram_group_id"],
                    recent_trends_text=row["recent_trends_text"],
                    analysis_message_count=row["analysis_message_count"],
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            ]

    async def find_latest_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, GroupTrend]:
        self.logger.debug(f"Fetching latest trend for {len(telegram_group_ids)} groups")
        placeholders = ",".join("?" * len(telegram_group_ids))
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT ai_group_trend_id, telegram_group_id,
                       recent_trends_text,
                       analysis_message_count, created_at
                FROM ai_group_trends t
                WHERE telegram_group_id IN ({placeholders})
                  AND ai_group_trend_id = (
                      SELECT MAX(ai_group_trend_id)
                      FROM ai_group_trends
                      WHERE telegram_group_id = t.telegram_group_id
                  )
                """,
                telegram_group_ids,
            )
            rows = await cursor.fetchall()
            return {
                row["telegram_group_id"]: GroupTrend.create(
                    ai_group_trend_id=row["ai_group_trend_id"],
                    telegram_group_id=row["telegram_group_id"],
                    recent_trends_text=row["recent_trends_text"],
                    analysis_message_count=row["analysis_message_count"],
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            }

    async def count_for_groups(self, telegram_group_ids: list[int]) -> dict[int, int]:
        self.logger.debug(f"Counting trends for {len(telegram_group_ids)} groups")
        placeholders = ",".join("?" * len(telegram_group_ids))
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT telegram_group_id, COUNT(*) as count
                FROM ai_group_trends
                WHERE telegram_group_id IN ({placeholders})
                GROUP BY telegram_group_id
                """,
                telegram_group_ids,
            )
            rows = await cursor.fetchall()
            return {row["telegram_group_id"]: row["count"] for row in rows}

    async def delete_all_for_group(self, telegram_group_id: int) -> None:
        self.logger.debug(f"Deleting all trends for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    "DELETE FROM ai_group_trends WHERE telegram_group_id = ?",
                    (telegram_group_id,),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error deleting trends for group {telegram_group_id}: {e}"
                )
                raise
