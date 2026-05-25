import uuid
from unittest.mock import patch

from backend.app.config import get_settings


def test_upload_requires_api_key_when_configured(api_client):
    get_settings.cache_clear()
    try:
        files = {"file": ("test.docx", b"x", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = api_client.post("/api/v1/upload", files=files)
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_upload_rejects_wrong_api_key(api_client, api_headers):
    headers = {**api_headers, "X-API-Key": "wrong"}
    files = {"file": ("test.docx", b"x", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    with patch("backend.app.api.routes.upload.persist_upload", return_value=uuid.uuid4()):
        response = api_client.post("/api/v1/upload", files=files, headers=headers)
    assert response.status_code == 401


def test_health_no_api_key(api_client):
    response = api_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
