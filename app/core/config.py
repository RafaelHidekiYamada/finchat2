from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = Field(min_length=32)
    database_url: str = "sqlite:///./finchat.db"
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if value.startswith(("SUBSTITUA", "COLE_AQUI")) or len(set(value)) < 10:
            raise ValueError("Configure SECRET_KEY com uma chave aleatória local.")
        return value

    @field_validator("database_url")
    @classmethod
    def normalize_database(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if not value.startswith(("sqlite:", "postgresql+psycopg:")):
            raise ValueError("Use SQLite ou PostgreSQL com psycopg.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
