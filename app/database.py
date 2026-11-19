from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.config import settings


class DatabaseManager:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Initialize a shared connection pool to PostgreSQL."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=5,
                max_size=25,
                max_inactive_connection_lifetime=300,
            )

    async def disconnect(self) -> None:
        """Gracefully close all database connections."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None


db_manager = DatabaseManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage database pool lifecycle across FastAPI startup and shutdown."""
    await db_manager.connect()
    try:
        yield
    finally:
        await db_manager.disconnect()
