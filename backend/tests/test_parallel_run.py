import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services import job_runner_service
from backend.app.services.pipeline_service import IN_PROGRESS


def test_fourth_run_returns_409_when_three_in_progress(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(id=job_id, status="pending")

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        with patch("backend.app.api.routes.jobs.count_in_progress", return_value=3):
            response = api_client.post(
                f"/api/v1/jobs/{job_id}/run",
                headers=api_headers,
            )
    assert response.status_code == 409
    body = response.json()
    assert "3" in str(body.get("detail", body))


def test_run_submits_via_job_runner(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(id=job_id, status="pending")
    runner = MagicMock()

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        with patch("backend.app.api.routes.jobs.count_in_progress", return_value=0):
            with patch("backend.app.api.routes.jobs.get_runner", return_value=runner):
                response = api_client.post(
                    f"/api/v1/jobs/{job_id}/run",
                    headers=api_headers,
                )
    assert response.status_code == 202
    runner.submit.assert_called_once_with(job_id)


def test_three_submits_when_slots_available(api_client, api_headers):
    runner = MagicMock()
    counts = iter([0, 1, 2])

    def _next_count():
        return next(counts)

    with patch("backend.app.api.routes.jobs.count_in_progress", side_effect=_next_count):
        with patch("backend.app.api.routes.jobs.get_runner", return_value=runner):
            with patch("backend.app.api.routes.jobs._get_record") as mock_get:
                for i in range(3):
                    mock_get.return_value = SimpleNamespace(
                        id=uuid.uuid4(), status="pending"
                    )
                    response = api_client.post(
                        f"/api/v1/jobs/{mock_get.return_value.id}/run",
                        headers=api_headers,
                    )
                    assert response.status_code == 202
    assert runner.submit.call_count == 3


def test_job_runner_max_workers_is_three():
    executor = job_runner_service._executor
    assert executor._max_workers == 3


def test_count_in_progress_excludes_pending():
    from backend.app.services.pipeline_service import count_in_progress

    session = MagicMock()
    session.scalar.return_value = 2
    assert count_in_progress(session=session) == 2
    stmt = session.scalar.call_args[0][0]
    assert IN_PROGRESS
