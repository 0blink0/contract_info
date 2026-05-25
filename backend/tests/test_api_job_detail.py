import uuid
from types import SimpleNamespace
from unittest.mock import patch


def test_job_detail_includes_warnings(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        filename="a.docx",
        status="extracted",
        error_message=None,
        product_xlsx_path=None,
        fee_xlsx_path=None,
        extraction_warnings=[
            {"field": "fund_code", "code": "missing", "message": "未抽取到基金代码"},
            {
                "field": "rate",
                "code": "low_confidence",
                "message": "费率置信度低",
                "suggestion": "请人工核对",
            },
        ],
        outline_preview=[{"title": "第一章"}],
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(f"/api/v1/jobs/{job_id}", headers=api_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_warnings_count"] == 2
    assert len(data["extraction_warnings"]) == 2
    assert data["extraction_warnings"][0]["field"] == "fund_code"
    assert data["extraction_warnings"][1]["suggestion"] == "请人工核对"
    assert data["outline_preview_count"] == 1
