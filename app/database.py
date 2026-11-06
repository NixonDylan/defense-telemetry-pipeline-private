import asyncpg
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings

class DatabaseManager:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Initializes a shared, reusable connection pool to PostgreSQL"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=5,     # Keep a minimum of 5 connections warm and waiting
                max_size=25,    # Scale up to 25 parallel database bridges under heavy stress
                max_inactive_connection_lifetime=300
            )

    async def disconnect(self):
        """Gracefully closes all database connections"""
        if self.pool:
            await self.pool.close()

db_manager = DatabaseManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles critical microservice startup and shutdown lifecycles"""
    await db_manager.connect()  # Establish database connection pool on start
    yield
    await db_manager.disconnect()  # Clean up connection resources on stop
