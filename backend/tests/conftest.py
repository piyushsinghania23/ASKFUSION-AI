import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = BACKEND_DIR / "test_askfusion.db"
UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"

os.environ.setdefault("ASKFUSION_DATABASE_URL", f"sqlite:///{TEST_DB_PATH.as_posix()}")
os.environ.setdefault("ASKFUSION_ENABLE_OPENAI", "false")

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_uploads():
    uploads = UPLOADS_DIR
    uploads.mkdir(parents=True, exist_ok=True)
    yield
    for child in uploads.glob("*"):
        if child.is_dir():
            for nested in child.glob("**/*"):
                if nested.is_file():
                    nested.unlink(missing_ok=True)
            for nested_dir in sorted(child.glob("**/*"), reverse=True):
                if nested_dir.is_dir():
                    nested_dir.rmdir()
            child.rmdir()
        else:
            child.unlink(missing_ok=True)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
