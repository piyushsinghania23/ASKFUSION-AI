from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings


settings = get_settings()


def _normalize_db_url(db_url: str) -> str:
    # Render Postgres URLs typically use "postgresql://".
    # Force SQLAlchemy to use psycopg v3 which is installed in this project.
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url[len("postgres://") :]
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url[len("postgresql://") :]
    return db_url


def _engine_kwargs(db_url: str) -> dict:
    if db_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


normalized_database_url = _normalize_db_url(settings.database_url)

engine = create_engine(
    normalized_database_url,
    pool_pre_ping=True,
    future=True,
    **_engine_kwargs(normalized_database_url),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
