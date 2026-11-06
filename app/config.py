import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Field names match incoming environment variables automatically
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "pipeline_transient_pass"
    POSTGRES_DB: str = "telemetry_db"
    POSTGRES_HOST: str = "localhost"  # Fallback to localhost for runner testing
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    JWT_SECRET_KEY: str = "super_secret_crypto_seal_key_change_me_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Pydantic v2 clean configuration dictionary mapping
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
