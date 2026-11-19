from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_DB: str = "telemetry_prod"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    # Required secrets (must be injected via environment variables)
    POSTGRES_PASSWORD: str = Field(..., min_length=8)
    JWT_SECRET_KEY: str = Field(..., min_length=16)

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
