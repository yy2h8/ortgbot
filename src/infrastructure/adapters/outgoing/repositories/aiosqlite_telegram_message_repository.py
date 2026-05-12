import logging
from datetime import datetime, timezone

from src.domain.entities import Message
from src.application.ports.telegram_message_repository import TelegramMessageRepository
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteTelegramMessageRepository(TelegramMessageRepository):
    """SQLite adapter implementing TelegramMessageRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def find_by_tg_id(self, tg_id: int) -> Message | None:
        self.logger.debug(f"Finding message by tg_id {tg_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_message_id, telegram_group_id, telegram_group_member_id,
                       reply_to_message_id, tg_id, content, timestamp,
                       is_reply_to_bot_message, is_generated, created_at
                FROM telegram_messages
                WHERE tg_id = ?
                """,
                (tg_id,),
            )
            row = await cursor.fetchone()

            return (
                Message.create(
                    telegram_message_id=row["telegram_message_id"],
                    telegram_group_id=row["telegram_group_id"],
                    telegram_group_member_id=row["telegram_group_member_id"],
                    reply_to_message_id=row["reply_to_message_id"],
                    tg_id=row["tg_id"],
                    content=row["content"],
                    timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                    is_reply_to_bot_message=bool(row["is_reply_to_bot_message"]),
                    is_generated=bool(row["is_generated"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def find_by_id(self, telegram_message_id: int) -> Message | None:
        self.logger.debug(
            f"Finding message by telegram_message_id {telegram_message_id}"
        )
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_message_id, telegram_group_id, telegram_group_member_id,
                       reply_to_message_id, tg_id, content, timestamp,
                       is_reply_to_bot_message, is_generated, created_at
                FROM telegram_messages
                WHERE telegram_message_id = ?
                """,
                (telegram_message_id,),
            )
            row = await cursor.fetchone()

            return (
                Message.create(
                    telegram_message_id=row["telegram_message_id"],
                    telegram_group_id=row["telegram_group_id"],
                    telegram_group_member_id=row["telegram_group_member_id"],
                    reply_to_message_id=row["reply_to_message_id"],
                    tg_id=row["tg_id"],
                    content=row["content"],
                    timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                    is_reply_to_bot_message=bool(row["is_reply_to_bot_message"]),
                    is_generated=bool(row["is_generated"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                if row
                else None
            )

    async def create(self, message: Message) -> Message:
        self.logger.debug(
            f"Creating message in group {message.telegram_group_id} with tg_id {message.tg_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    INSERT INTO telegram_messages
                    (telegram_group_id, telegram_group_member_id,
                     reply_to_message_id, tg_id, content, timestamp,
                     is_reply_to_bot_message, is_generated, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.telegram_group_id,
                        message.telegram_group_member_id,
                        message.reply_to_message_id,
                        message.tg_id,
                        message.content,
                        int(message.timestamp.timestamp()),
                        int(message.is_reply_to_bot_message),
                        int(message.is_generated),
                        int(message.created_at.timestamp()),
                    ),
                )
                await conn.commit()
                return message._replace(telegram_message_id=cursor.lastrowid)
            except Exception as e:
                self.logger.error(f"Error creating telegram message: {e}")
                raise

    async def get_replies_for_message(self, message_id: int) -> list[Message]:
        self.logger.debug(f"Retrieving reply thread for message {message_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                WITH RECURSIVE reply_thread AS (
                    SELECT telegram_message_id, telegram_group_id, telegram_group_member_id,
                           reply_to_message_id, tg_id, content, timestamp,
                           is_reply_to_bot_message, is_generated, created_at
                    FROM telegram_messages
                    WHERE telegram_message_id = ?
                    
                    UNION ALL
                    
                    SELECT m.telegram_message_id, m.telegram_group_id, m.telegram_group_member_id,
                           m.reply_to_message_id, m.tg_id, m.content, m.timestamp,
                           m.is_reply_to_bot_message, m.is_generated, m.created_at
                    FROM telegram_messages m
                    INNER JOIN reply_thread rt ON m.telegram_message_id = rt.reply_to_message_id
                )
                SELECT telegram_message_id, telegram_group_id, telegram_group_member_id,
                       reply_to_message_id, tg_id, content, timestamp,
                       is_reply_to_bot_message, is_generated, created_at
                FROM reply_thread
                ORDER BY timestamp ASC
                """,
                (message_id,),
            )
            rows = await cursor.fetchall()
            return [
                Message.create(
                    telegram_message_id=row["telegram_message_id"],
                    telegram_group_id=row["telegram_group_id"],
                    telegram_group_member_id=row["telegram_group_member_id"],
                    reply_to_message_id=row["reply_to_message_id"],
                    tg_id=row["tg_id"],
                    content=row["content"],
                    timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                    is_reply_to_bot_message=bool(row["is_reply_to_bot_message"]),
                    is_generated=bool(row["is_generated"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            ]

    async def get_all_messages_for_group_excluding_generated(
        self, group_id: int
    ) -> list[Message]:
        self.logger.debug(f"Retrieving all non-generated messages for group {group_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_message_id, telegram_group_id, telegram_group_member_id,
                       reply_to_message_id, tg_id, content, timestamp,
                       is_reply_to_bot_message, is_generated, created_at
                FROM telegram_messages
                WHERE telegram_group_id = ? AND is_generated = 0
                ORDER BY timestamp ASC
                """,
                (group_id,),
            )
            rows = await cursor.fetchall()
            return [
                Message.create(
                    telegram_message_id=row["telegram_message_id"],
                    telegram_group_id=row["telegram_group_id"],
                    telegram_group_member_id=row["telegram_group_member_id"],
                    reply_to_message_id=row["reply_to_message_id"],
                    tg_id=row["tg_id"],
                    content=row["content"],
                    timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                    is_reply_to_bot_message=bool(row["is_reply_to_bot_message"]),
                    is_generated=bool(row["is_generated"]),
                    created_at=datetime.fromtimestamp(
                        row["created_at"], tz=timezone.utc
                    ),
                )
                for row in rows
            ]

    async def delete_all_for_group(self, telegram_group_id: int) -> None:
        self.logger.info(f"Deleting all messages for group {telegram_group_id}")
        async with self._db.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    DELETE FROM telegram_messages
                    WHERE telegram_group_id = ?
                    """,
                    (telegram_group_id,),
                )
                await conn.commit()
                self.logger.info(
                    f"Successfully deleted all messages for group {telegram_group_id}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error deleting all messages for group {telegram_group_id}: {e}"
                )
                raise

    async def count_non_generated_for_groups(
        self, telegram_group_ids: list[int]
    ) -> dict[int, int]:
        self.logger.debug(
            f"Counting non-generated messages for {len(telegram_group_ids)} groups"
        )
        placeholders = ",".join("?" * len(telegram_group_ids))
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT telegram_group_id, COUNT(*) AS count
                FROM telegram_messages
                WHERE telegram_group_id IN ({placeholders}) AND is_generated = 0
                GROUP BY telegram_group_id
                """,
                telegram_group_ids,
            )
            rows = await cursor.fetchall()
            return {row["telegram_group_id"]: row["count"] for row in rows}
