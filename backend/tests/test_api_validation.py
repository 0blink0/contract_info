import uuid
from types import SimpleNamespace
from unittest.mock import patch


def test_validation_requires_extracted(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="parsed",
        validation_result=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/validation",
            headers=api_headers,
        )
    assert response.status_code == 409


def test_validation_success(api_client, api_headers):
    job_id = uuid.uuid4()
    payload = {
        "validated_at": "2026-05-26T00:00:00+00:00",
        "model": "mock",
        "skipped": False,
        "items": [
            {
                "field": "管理人",
                "status": "fail",
                "value": "北京石云",
                "reason": "与摘录矛盾",
            }
        ],
        "summary": {"pass": 0, "warn": 0, "fail": 1},
    }
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        validation_result=payload,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/validation",
            headers=api_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["fail"] == 1
    assert body["items"][0]["status"] == "fail"


def test_validation_missing_result(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        validation_result=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/validation",
            headers=api_headers,
        )
    assert response.status_code == 404


def test_job_detail_validation_counts(api_client, api_headers):
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
        path_b_json=None,
        validation_result={
            "summary": {"pass": 2, "warn": 1, "fail": 3},
            "items": [],
        },
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}",
            headers=api_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["validation_available"] is True
    assert body["validation_fail_count"] == 3
    assert body["validation_warn_count"] == 1
