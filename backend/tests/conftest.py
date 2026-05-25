import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = PROJECT_ROOT / "example"


def pytest_configure(config):
    config.addinivalue_line("markers", "llm: requires OPENAI_API_KEY")
    config.addinivalue_line("markers", "integration: requires DATABASE_URL")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def example_docx_path() -> Path:
    candidates = sorted(EXAMPLE_DIR.glob("*.docx"))
    if not candidates:
        pytest.skip("No example/*.docx found")
    return candidates[0]


@pytest.fixture
def db_session():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — skip integration tests")
    from backend.app.db.session import SessionLocal
    from backend.app.models import ContractFile

    session = SessionLocal()
    created_ids: list = []
    try:
        yield session, created_ids
    finally:
        for file_id in created_ids:
            row = session.get(ContractFile, file_id)
            if row:
                session.delete(row)
        session.commit()
        session.close()


@pytest.fixture
def api_settings(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    from backend.app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def api_client(api_settings):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    return TestClient(app)


@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key"}
