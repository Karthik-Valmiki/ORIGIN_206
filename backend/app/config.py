from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:pass123@localhost:5432/ORIGIN_DB"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "./uploads"

    # ── Hardcoded Admin Credentials (seeded automatically on startup) ──
    ADMIN_EMAIL: str = "admin@lmpc.gov.in"
    ADMIN_PASSWORD: str = "Admin@2026"
    ADMIN_FULL_NAME: str = "System Administrator"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
