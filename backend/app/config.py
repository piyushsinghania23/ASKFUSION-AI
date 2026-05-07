from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_DB_PATH = BACKEND_DIR / "askfusion.db"
DEFAULT_UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


class Settings(BaseSettings):
    app_name: str = "ASKFUSION AI"
    environment: str = "development"
    database_url: str = _sqlite_url(DEFAULT_DB_PATH)
    uploads_dir: Path = DEFAULT_UPLOADS_DIR
    chunk_size: int = 140
    chunk_overlap: int = 24
    max_upload_size_mb: int = 150

    # Accept both project-prefixed and common provider env var names.
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ASKFUSION_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    enable_openai: bool = True
    chat_model: str = "gpt-5.2"
    embedding_model: str = "text-embedding-3-small"
    transcription_model: str = "whisper-1"

    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    allowed_origin_regex: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="ASKFUSION_",
        env_file=(str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    return settings
