import os
from contextlib import asynccontextmanager
import logging

import aiosqlite


class AiosqliteDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._connection: aiosqlite.Connection | None = None

    async def create_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            # Ensure directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            self._connection = await aiosqlite.connect(self.db_path)

            # performance
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA foreign_keys=ON")
            await self._connection.execute("PRAGMA cache_size=-6000")
            await self._connection.execute("PRAGMA temp_store=MEMORY")
            await self._connection.execute("PRAGMA busy_timeout=5000")
            await self._connection.execute("PRAGMA synchronous=NORMAL")

            # Set row factory for dictionary-like access
            self._connection.row_factory = aiosqlite.Row
            self.logger.info(f"Created SQLite connection: {self.db_path}")

        return self._connection

    async def close_connection(self):
        if self._connection:
            await self._connection.close()
            self.logger.info("Closed SQLite connection")
            self._connection = None

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection for database operations.

        Usage:
            async with db.get_connection() as conn:
                await conn.execute("SELECT * FROM table")
        """
        conn = await self.create_connection()
        yield conn

    async def init_schema(self, schema_path: str = None):
        """Initialize database schema from SQL file"""

        if schema_path is None:
            schema_path = os.path.join(os.path.dirname(__file__), "schema_sqlite.sql")

        if not os.path.exists(schema_path):
            self.logger.warning(f"Schema file not found: {schema_path}")
            return

        with open(schema_path, "r") as f:
            schema = f.read()

        async with self.get_connection() as conn:
            await conn.executescript(schema)
            await conn.commit()

        self.logger.info(f"Initialized schema from {schema_path}")
