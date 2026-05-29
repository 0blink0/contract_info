import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services.pipeline_service import can_run


def test_can_run_pending():
    assert can_run("pending") is True


def test_can_run_parsing_busy():
    assert can_run("parsing") is False


def test_run_returns_202(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(id=job_id, status="pending")

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        with patch("backend.app.api.routes.jobs.count_in_progress", return_value=0):
            with patch("backend.app.api.routes.jobs.get_runner") as mock_runner:
                mock_runner.return_value.submit = MagicMock()
                response = api_client.post(
                    f"/api/v1/jobs/{job_id}/run",
                    headers=api_headers,
                )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_run_conflict_when_exporting(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(id=job_id, status="exporting")

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.post(
            f"/api/v1/jobs/{job_id}/run",
            headers=api_headers,
        )
    assert response.status_code == 409
