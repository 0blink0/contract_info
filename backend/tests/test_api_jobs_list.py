import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

def test_list_jobs_empty(api_client, api_headers):
    mock_session = MagicMock()
    mock_session.scalars.return_value.all.return_value = []
    with patch("backend.app.api.routes.jobs.SessionLocal", return_value=mock_session):
        response = api_client.get("/api/v1/jobs?limit=10", headers=api_headers)
    assert response.status_code == 200
    assert response.json() == {"items": []}
    mock_session.close.assert_called()


def test_list_jobs_limit_up_to_200(api_client, api_headers):
    mock_session = MagicMock()
    mock_session.scalars.return_value.all.return_value = []
    with patch("backend.app.api.routes.jobs.SessionLocal", return_value=mock_session):
        ok = api_client.get("/api/v1/jobs?limit=100", headers=api_headers)
        bad = api_client.get("/api/v1/jobs?limit=201", headers=api_headers)
    assert ok.status_code == 200
    assert bad.status_code == 422


def test_list_jobs_returns_items(api_client, api_headers):
    job_id = uuid.uuid4()
    row = SimpleNamespace(
        id=job_id,
        filename="合同.docx",
        status="pending",
        created_at=datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc),
    )
    mock_session = MagicMock()
    mock_session.scalars.return_value.all.return_value = [row]
    with patch("backend.app.api.routes.jobs.SessionLocal", return_value=mock_session):
        response = api_client.get("/api/v1/jobs", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["job_id"] == str(job_id)
    assert data["items"][0]["filename"] == "合同.docx"
    assert data["items"][0]["status"] == "pending"
