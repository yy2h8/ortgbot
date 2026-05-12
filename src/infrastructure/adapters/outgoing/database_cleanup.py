import logging
from datetime import datetime, timezone

from src.infrastructure.core.database import AiosqliteDatabase


class DatabaseCleanup:
    def __init__(
        self,
        db: AiosqliteDatabase,
        inactive_cleanup_days: int,
        logger: logging.Logger,
    ):
        self._db = db
        self._inactive_cleanup_days = inactive_cleanup_days
        self.logger = logger

    async def cleanup(self) -> tuple[int, int]:
        deleted_groups = await self._cleanup_inactive_groups()
        await self._cleanup_orphaned_records()
        deleted_members = await self._cleanup_inactive_members()
        await self._cleanup_orphaned_member_messages()
        return deleted_groups, deleted_members

    async def _cleanup_inactive_groups(self) -> int:
        cutoff = int(datetime.now(timezone.utc).timestamp()) - (
            self._inactive_cleanup_days * 86400
        )

        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    SELECT telegram_group_id
                    FROM telegram_groups
                    WHERE is_active = 0 AND updated_at < ?
                    """,
                    (cutoff,),
                )
                rows = await cursor.fetchall()
                group_ids = [row["telegram_group_id"] for row in rows]

                if not group_ids:
                    self.logger.info("No inactive groups to clean up")
                    return 0

                placeholders = ",".join("?" * len(group_ids))
                try:
                    await conn.execute(
                        f"DELETE FROM telegram_messages WHERE telegram_group_id IN ({placeholders})",
                        group_ids,
                    )
                    await conn.execute(
                        f"DELETE FROM ai_group_trends WHERE telegram_group_id IN ({placeholders})",
                        group_ids,
                    )
                    await conn.execute(
                        f"DELETE FROM ai_group_contexts WHERE telegram_group_id IN ({placeholders})",
                        group_ids,
                    )
                    await conn.execute(
                        f"DELETE FROM telegram_group_members WHERE telegram_group_id IN ({placeholders})",
                        group_ids,
                    )
                    await conn.execute(
                        f"DELETE FROM telegram_groups WHERE telegram_group_id IN ({placeholders})",
                        group_ids,
                    )
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    self.logger.error(f"Failed to delete inactive groups: {e}")
                    raise

                self.logger.info(f"Deleted {len(group_ids)} inactive groups")
                return len(group_ids)
            except Exception as e:
                self.logger.error(f"Error during inactive group cleanup: {e}")
                raise

    async def _cleanup_orphaned_records(self) -> None:
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    "DELETE FROM telegram_messages WHERE telegram_group_id IS NULL"
                )
                await conn.execute(
                    "DELETE FROM ai_group_trends WHERE telegram_group_id IS NULL"
                )
                await conn.execute(
                    "DELETE FROM ai_group_contexts WHERE telegram_group_id IS NULL"
                )
                await conn.execute(
                    "DELETE FROM telegram_group_members WHERE telegram_group_id IS NULL"
                )
                await conn.commit()
                self.logger.info("Cleaned up orphaned records with NULL group_id")
            except Exception as e:
                self.logger.error(f"Error during orphan cleanup: {e}")
                raise

    async def _cleanup_inactive_members(self) -> int:
        cutoff = int(datetime.now(timezone.utc).timestamp()) - (
            self._inactive_cleanup_days * 86400
        )

        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    SELECT m.telegram_group_member_id
                    FROM telegram_group_members m
                    INNER JOIN telegram_groups g
                        ON m.telegram_group_id = g.telegram_group_id
                    WHERE m.has_left_group = 1
                        AND m.updated_at < ?
                        AND g.is_active = 1
                    """,
                    (cutoff,),
                )
                rows = await cursor.fetchall()
                member_ids = [row["telegram_group_member_id"] for row in rows]

                if not member_ids:
                    self.logger.info("No inactive members to clean up")
                    return 0

                placeholders = ",".join("?" * len(member_ids))
                try:
                    await conn.execute(
                        f"DELETE FROM telegram_messages WHERE telegram_group_member_id IN ({placeholders})",
                        member_ids,
                    )
                    await conn.execute(
                        f"DELETE FROM telegram_group_members WHERE telegram_group_member_id IN ({placeholders})",
                        member_ids,
                    )
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    self.logger.error(f"Failed to delete inactive members: {e}")
                    raise

                self.logger.info(f"Deleted {len(member_ids)} inactive members")
                return len(member_ids)
            except Exception as e:
                self.logger.error(f"Error during inactive member cleanup: {e}")
                raise

    async def _cleanup_orphaned_member_messages(self) -> None:
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    DELETE FROM telegram_messages
                    WHERE telegram_group_member_id IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM telegram_group_members gm
                            WHERE gm.telegram_group_member_id = telegram_messages.telegram_group_member_id
                        )
                    """
                )
                await conn.commit()
                self.logger.info("Cleaned up messages referencing deleted members")
            except Exception as e:
                self.logger.error(f"Error during orphaned member message cleanup: {e}")
                raise
