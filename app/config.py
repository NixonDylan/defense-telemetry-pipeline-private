import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = "telemetry_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Using a try/except guard lets your local unit tests load or fail elegantly
try:
    settings = Settings()
except Exception as e:
    # Intentionally crash early if a developer forgot to export environmental variables
    raise RuntimeError(f"DevSecOps Initialization Failure: Missing required secure keys. {str(e)}")
