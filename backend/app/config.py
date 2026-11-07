from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "AttendanceSystem"
    debug: bool = False
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'attendance.db').as_posix()}"
    secret_key: str = "dev-secret-change-me"
    session_expire_days: int = 7
    max_upload_mb: int = 5
    upload_dir: str = str(BASE_DIR / "uploads")

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
