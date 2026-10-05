from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = Field(
        min_length=32,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    database_url: str = "sqlite:///./finchat.db"
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    cors_origins: str = "http://localhost:5173"
    llm_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)

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

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM deve ser HS256 neste checkpoint.")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS deve listar origens explícitas.")
        if any(not origin.startswith(("http://", "https://")) for origin in origins):
            raise ValueError("CORS_ORIGINS contém uma origem inválida.")
        return ",".join(origins)

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL deve ser uma URL HTTP válida.")
        return value

    @field_validator("ollama_model")
    @classmethod
    def validate_ollama_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("OLLAMA_MODEL não pode ficar vazio.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return self.cors_origins.split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
