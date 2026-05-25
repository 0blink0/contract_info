import uuid
from unittest.mock import patch


def test_upload_rejects_non_docx(api_client, api_headers):
    files = {"file": ("contract.pdf", b"x", "application/pdf")}
    response = api_client.post("/api/v1/upload", files=files, headers=api_headers)
    assert response.status_code == 400


def test_upload_success_pending(api_client, api_headers):
    job_id = uuid.uuid4()
    with patch("backend.app.api.routes.upload.persist_upload", return_value=job_id):
        files = {
            "file": (
                "contract.docx",
                b"PK",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = api_client.post("/api/v1/upload", files=files, headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "pending"
    assert data["filename"] == "contract.docx"
