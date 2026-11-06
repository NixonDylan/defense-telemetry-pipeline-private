import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Pull individual DB configuration blocks
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "secure_db_pass_change_me")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "telemetry_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Dynamic async connection string creation
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super_secret_crypto_seal_key_change_me_in_prod")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
