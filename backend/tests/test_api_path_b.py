import uuid
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.config import PROJECT_ROOT


def test_path_b_requires_extracted(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="parsed",
        path_b_json=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/path-b",
            headers=api_headers,
        )
    assert response.status_code == 409


def test_path_b_success(api_client, api_headers):
    job_id = uuid.uuid4()
    payload = {
        "performance_fee": {"tiers": [{"share_class": "A", "description": "test"}]},
        "open_day": {"fixed_schedule": "每月开放"},
        "source_snippets": {"open_day.fixed_schedule": "每月开放"},
    }
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        path_b_json=payload,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/path-b",
            headers=api_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["performance_fee"]["tiers"]
    assert body["open_day"]["fixed_schedule"] == "每月开放"
    assert body["source_snippets"]["open_day.fixed_schedule"]


def test_path_b_missing_json(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        path_b_json=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/path-b",
            headers=api_headers,
        )
    assert response.status_code == 404


def test_job_detail_path_b_available(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        filename="a.docx",
        error_message=None,
        extraction_warnings=[],
        outline_preview=None,
        product_xlsx_path=None,
        fee_xlsx_path=None,
        lock_xlsx_path=None,
        share_xlsx_path=None,
        subscription_xlsx_path=None,
        path_b_json={"open_day": {}},
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}",
            headers=api_headers,
        )
    assert response.status_code == 200
    assert response.json()["path_b_available"] is True
