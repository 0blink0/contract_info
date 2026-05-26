import uuid
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.preview_service import build_job_preview


def test_build_preview_from_extraction():
    record = SimpleNamespace(
        id=uuid.uuid4(),
        status="exported",
        product_xlsx_path=None,
        fee_xlsx_path=None,
        extraction_result={
            "product_elements": {
                "基金全称": {"value": "测试基金"},
            },
            "fee_rates": [
                {
                    "基金名称": "测试基金",
                    "运营费类型": "管理费",
                    "rate_annual_pct": "1.5",
                },
            ],
        },
    )
    data = build_job_preview(record)
    assert data["source"] == "extraction"
    assert len(data["product_rows"]) == 1
    assert data["product_rows"][0]["field"] == "基金全称"
    assert len(data["fee_rows"]) == 1


def test_preview_api(api_client, api_headers):
    job_id = uuid.uuid4()
    with patch(
        "backend.app.api.routes.jobs.get_job_preview",
        return_value={
            "job_id": job_id,
            "source": "extraction",
            "product_rows": [{"field": "基金全称", "value": "A"}],
            "fee_columns": ["运营费类型"],
            "fee_rows": [{"运营费类型": "管理费"}],
        },
    ):
        res = api_client.get(f"/api/v1/jobs/{job_id}/preview", headers=api_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["product_rows"][0]["field"] == "基金全称"
