import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SaaS Queue System"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "SUPER_SECRET_JWT_KEY_FOR_EL_PUNTANO_SAAS_12345" # In production, load from env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database configuration (defaults to a local async SQLite db)
    DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
