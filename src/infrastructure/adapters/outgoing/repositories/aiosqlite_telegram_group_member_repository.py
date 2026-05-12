import logging
from datetime import datetime, timezone

from src.domain.entities import GroupMember
from src.application.ports.telegram_group_member_repository import (
    TelegramGroupMemberRepository,
)
from src.infrastructure.core.database import AiosqliteDatabase


class AiosqliteTelegramGroupMemberRepository(TelegramGroupMemberRepository):
    """SQLite adapter implementing TelegramGroupMemberRepository port"""

    def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
        self._db = db
        self.logger = logger

    async def find_by_tg_and_group_id(
        self, tg_id: int, telegram_group_id: int
    ) -> GroupMember | None:
        self.logger.debug(
            f"Finding member with tg_id={tg_id} in group {telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_group_member_id, telegram_group_id, tg_id, first_name,
                       username, has_left_group, created_at, updated_at
                FROM telegram_group_members
                WHERE tg_id = ? AND telegram_group_id = ?
                """,
                (tg_id, telegram_group_id),
            )
            row = await cursor.fetchone()

            return (
                GroupMember.create(
                    telegram_group_member_id=row["telegram_group_member_id"],
                    telegram_group_id=row["telegram_group_id"],
                    tg_id=row["tg_id"],
                    first_name=row["first_name"],
                    username=row["username"],
                    has_left_group=bool(row["has_left_group"]),
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

    async def find_by_id(self, telegram_group_member_id: int) -> GroupMember | None:
        self.logger.debug(f"Finding member with id={telegram_group_member_id}")
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT telegram_group_member_id, telegram_group_id, tg_id, first_name,
                       username, has_left_group, created_at, updated_at
                FROM telegram_group_members
                WHERE telegram_group_member_id = ?
                """,
                (telegram_group_member_id,),
            )
            row = await cursor.fetchone()

            return (
                GroupMember.create(
                    telegram_group_member_id=row["telegram_group_member_id"],
                    telegram_group_id=row["telegram_group_id"],
                    tg_id=row["tg_id"],
                    first_name=row["first_name"],
                    username=row["username"],
                    has_left_group=bool(row["has_left_group"]),
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

    async def create(self, member: GroupMember) -> GroupMember:
        self.logger.debug(
            f"Creating member with tg_id={member.tg_id} in group {member.telegram_group_id}"
        )
        async with self._db.get_connection() as conn:
            try:
                cursor = await conn.execute(
                    """
                    INSERT INTO telegram_group_members
                    (telegram_group_id, tg_id, first_name,
                     username, has_left_group, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        member.telegram_group_id,
                        member.tg_id,
                        member.first_name,
                        member.username,
                        int(member.has_left_group),
                        int(member.created_at.timestamp()),
                        int(member.updated_at.timestamp()),
                    ),
                )
                await conn.commit()
                return member._replace(telegram_group_member_id=cursor.lastrowid)
            except Exception as e:
                self.logger.error(f"Error creating telegram group member: {e}")
                raise

    async def mark_member_left(self, telegram_group_member_id: int) -> None:
        self.logger.info(f"Marking member {telegram_group_member_id} as left")
        async with self._db.get_connection() as conn:
            try:
                now = int(datetime.now(timezone.utc).timestamp())
                cursor = await conn.execute(
                    """
                    UPDATE telegram_group_members
                    SET has_left_group = 1,
                        updated_at = ?
                    WHERE telegram_group_member_id = ?
                    """,
                    (now, telegram_group_member_id),
                )
                await conn.commit()
                self.logger.info(
                    f"Successfully marked member {telegram_group_member_id} as left"
                )
            except Exception as e:
                self.logger.error(
                    f"Error marking member {telegram_group_member_id} as left: {e}"
                )
                raise

    async def update_member_info(
        self,
        telegram_group_member_id: int,
        first_name: str,
        username: str | None,
    ) -> None:
        self.logger.debug(f"Updating info for member {telegram_group_member_id}")
        async with self._db.get_connection() as conn:
            try:
                now = int(datetime.now(timezone.utc).timestamp())
                cursor = await conn.execute(
                    """
                    UPDATE telegram_group_members
                    SET first_name = ?,
                        username = ?,
                        updated_at = ?
                    WHERE telegram_group_member_id = ?
                    """,
                    (
                        first_name,
                        username,
                        now,
                        telegram_group_member_id,
                    ),
                )
                await conn.commit()
            except Exception as e:
                self.logger.error(
                    f"Error updating member info for {telegram_group_member_id}: {e}"
                )
                raise
