import uuid
from types import SimpleNamespace
from unittest.mock import patch

FULL_PREVIEW = {
    "job_id": uuid.uuid4(),
    "source": "extraction",
    "product_rows": [{"field": "基金全称", "value": "测试"}],
    "fee_columns": ["管理费率"],
    "fee_rows": [{"管理费率": "1%"}],
    "lock_columns": [],
    "lock_rows": [],
    "share_columns": [],
    "share_rows": [],
    "subscription_columns": [],
    "subscription_rows": [],
}


def test_get_section_fee_matches_full(api_client, api_headers):
    job_id = FULL_PREVIEW["job_id"]
    section_payload = {
        **FULL_PREVIEW,
        "job_id": job_id,
        "section": "fee-rates",
    }
    with patch(
        "backend.app.api.routes.jobs.get_job_preview_section",
        return_value=section_payload,
    ):
        section_resp = api_client.get(
            f"/api/v1/jobs/{job_id}/preview/fee-rates",
            headers=api_headers,
        )
    with patch("backend.app.api.routes.jobs.get_job_preview", return_value=FULL_PREVIEW):
        full_resp = api_client.get(
            f"/api/v1/jobs/{job_id}/preview",
            headers=api_headers,
        )
    assert section_resp.status_code == 200
    assert full_resp.status_code == 200
    assert section_resp.json()["fee_rows"] == full_resp.json()["fee_rows"]


def test_put_section_returns_200(api_client, api_headers):
    job_id = uuid.uuid4()
    with patch(
        "backend.app.api.routes.jobs.apply_section_preview_edits",
        return_value=FULL_PREVIEW | {"job_id": job_id},
    ):
        response = api_client.put(
            f"/api/v1/jobs/{job_id}/preview/product-elements",
            headers=api_headers,
            json={"product_rows": [{"field": "基金全称", "value": "新"}]},
        )
    assert response.status_code == 200
    assert response.json()["section"] == "product-elements"


def test_invalid_section_422(api_client, api_headers):
    job_id = uuid.uuid4()
    response = api_client.get(
        f"/api/v1/jobs/{job_id}/preview/not-a-section",
        headers=api_headers,
    )
    assert response.status_code == 422
