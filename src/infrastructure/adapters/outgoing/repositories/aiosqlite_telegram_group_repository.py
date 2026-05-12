import logging
from datetime import datetime, timezone

from src.domain.entities import Group
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteTelegramGroupRepository(TelegramGroupRepository):
    """SQLite adapter implementing TelegramGroupRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def find_by_tg_id(self, tg_id: int) -> Group | None:
        self.logger.debug(f"Finding group by tg_id {tg_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_group_id, tg_id, title, language,
                       trigger_word, persona, bot_added_at, is_active,
                       created_at, updated_at
                FROM telegram_groups
                WHERE tg_id = ?
                """,
                (tg_id,),
            )
            row = await cursor.fetchone()

            return (
                Group.create(
                    telegram_group_id=row["telegram_group_id"],
                    tg_id=row["tg_id"],
                    title=row["title"],
                    language=row["language"],
                    trigger_word=row["trigger_word"],
                    persona=row["persona"],
                    bot_added_at=datetime.fromtimestamp(
                        row["bot_added_at"], tz=timezone.utc
                    ),
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                    updated_at=datetime.fromtimestamp(
                        row["updated_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def find_by_id(self, telegram_group_id: int) -> Group | None:
        self.logger.debug(
            f"Finding active group by telegram_group_id {telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_group_id, tg_id, title, language,
                       trigger_word, persona, bot_added_at, is_active,
                       created_at, updated_at
                FROM telegram_groups
                WHERE telegram_group_id = ? AND is_active = 1
                """,
                (telegram_group_id,),
            )
            row = await cursor.fetchone()

            return (
                Group.create(
                    telegram_group_id=row["telegram_group_id"],
                    tg_id=row["tg_id"],
                    title=row["title"],
                    language=row["language"],
                    trigger_word=row["trigger_word"],
                    persona=row["persona"],
                    bot_added_at=datetime.fromtimestamp(
                        row["bot_added_at"], tz=timezone.utc
                    ),
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                    updated_at=datetime.fromtimestamp(
                        row["updated_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def find_active_groups(self) -> list[Group]:
        self.logger.debug("Finding all active groups")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_group_id, tg_id, title, language,
                       trigger_word, persona, bot_added_at, is_active,
                       created_at, updated_at
                FROM telegram_groups
                WHERE language IS NOT NULL AND is_active = 1
                ORDER BY updated_at DESC
                """
            )
            rows = await cursor.fetchall()
            return [
                Group.create(
                    telegram_group_id=row["telegram_group_id"],
                    tg_id=row["tg_id"],
                    title=row["title"],
                    language=row["language"],
                    trigger_word=row["trigger_word"],
                    persona=row["persona"],
                    bot_added_at=datetime.fromtimestamp(
                        row["bot_added_at"], tz=timezone.utc
                    ),
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                    updated_at=datetime.fromtimestamp(
                        row["updated_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            ]

    async def create(self, group: Group) -> Group:
        self.logger.info(
            f"Creating new telegram group with tg_id {group.tg_id} and title '{group.title}'"
        )
        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    INSERT INTO telegram_groups
                    (tg_id, title, language, trigger_word,
                     bot_added_at, is_active,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group.tg_id,
                        group.title,
                        group.language,
                        group.trigger_word,
                        int(group.bot_added_at.timestamp()),
                        int(group.is_active),
                        int(group.created_at.timestamp()),
                        int(group.updated_at.timestamp()),
                    ),
                )
                await conn.commit()
                return group._replace(telegram_group_id=cursor.lastrowid)
            except Exception as e:
                self.logger.error(f"Error creating telegram group: {e}")
                raise

    async def deactivate_group(self, tg_id: int) -> None:
        self.logger.info(f"Deactivating group with tg_id {tg_id}")
        async with self._db.get_connection() as conn:
            try:
                now = int(datetime.now(timezone.utc).timestamp())
                cursor = await conn.execute(
                    """
                    UPDATE telegram_groups
                    SET is_active = 0, updated_at = ?
                    WHERE tg_id = ?
                    """,
                    (now, tg_id),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(f"Error deactivating group {tg_id}: {e}")
                raise

    async def reactivate_group(self, telegram_group_id: int, title: str) -> None:
        self.logger.info(
            f"Reactivating group with telegram_group_id {telegram_group_id} and title '{title}'"
        )
        async with self._db.get_connection() as conn:
            try:
                now = int(datetime.now(timezone.utc).timestamp())
                cursor = await conn.execute(
                    """
                    UPDATE telegram_groups
                    SET is_active = 1,
                        title = ?,
                        bot_added_at = ?,
                        updated_at = ?
                    WHERE telegram_group_id = ?
                    """,
                    (title, now, now, telegram_group_id),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(f"Error reactivating group {telegram_group_id}: {e}")
                raise

    async def set_language(self, telegram_group_id: int, language: str) -> None:
        self.logger.info(
            f"Setting language '{language}' for group with telegram_group_id {telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE telegram_groups
                    SET language = ?
                    WHERE telegram_group_id = ?
                    """,
                    (language, telegram_group_id),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error setting language for group {telegram_group_id}: {e}"
                )
                raise

    async def set_trigger_word(self, telegram_group_id: int, trigger_word: str) -> None:
        self.logger.info(
            f"Setting trigger word '{trigger_word}' for group with telegram_group_id {telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                now = int(datetime.now(timezone.utc).timestamp())
                await conn.execute(
                    """
                    UPDATE telegram_groups
                    SET trigger_word = ?, updated_at = ?
                    WHERE telegram_group_id = ?
                    """,
                    (trigger_word, now, telegram_group_id),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error setting trigger word for group {telegram_group_id}: {e}"
                )
                raise

    async def set_persona(self, telegram_group_id: int, persona: str | None) -> None:
        self.logger.info(
            f"Setting persona for group with telegram_group_id {telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE telegram_groups
                    SET persona = ?
                    WHERE telegram_group_id = ?
                    """,
                    (persona, telegram_group_id),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error setting persona for group {telegram_group_id}: {e}"
                )
                raise
