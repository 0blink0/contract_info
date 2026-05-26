import uuid
from unittest.mock import patch

from backend.app.services.delete_service import JobDeleteBusyError, delete_job_record


def test_delete_job_record_calls_cleanup():
    job_id = uuid.uuid4()
    with patch("backend.app.services.delete_service.SessionLocal") as mock_session_cls:
        session = mock_session_cls.return_value
        record = type("R", (), {"status": "exported"})()
        session.get.return_value = record
        with patch("backend.app.services.delete_service._remove_tree") as mock_rm:
            delete_job_record(job_id)
        session.delete.assert_called_once_with(record)
        session.commit.assert_called_once()
        assert mock_rm.call_count == 2


def test_delete_api(api_client, api_headers):
    job_id = uuid.uuid4()
    with patch("backend.app.api.routes.jobs.delete_job_record"):
        res = api_client.delete(f"/api/v1/jobs/{job_id}", headers=api_headers)
    assert res.status_code == 200
    assert res.json()["job_id"] == str(job_id)


def test_delete_busy_returns_409(api_client, api_headers):
    job_id = uuid.uuid4()
    with patch(
        "backend.app.api.routes.jobs.delete_job_record",
        side_effect=JobDeleteBusyError("parsing"),
    ):
        res = api_client.delete(f"/api/v1/jobs/{job_id}", headers=api_headers)
    assert res.status_code == 409
