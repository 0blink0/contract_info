from unittest.mock import AsyncMock, Mock, patch

KB_ENTRY_PAYLOAD = {
    "entries": [
        {
            "field_name": "业绩报酬提取方式",
            "field_value": "基金整体资产高水位法",
            "snippet": "",
            "source_job_id": "job-uuid-1",
            "source_filename": "test.docx",
        }
    ]
}


def test_post_entries_success(api_client, api_headers):
    mock_svc = Mock()
    mock_svc.model_available = True
    mock_svc.add_entries = AsyncMock(return_value=["test-uuid-1"])
    with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
        resp = api_client.post("/api/v1/kb/entries", json=KB_ENTRY_PAYLOAD, headers=api_headers)
    assert resp.status_code == 200
    assert resp.json() == {"ids": ["test-uuid-1"], "count": 1}


def test_post_entries_503_when_no_model(api_client, api_headers):
    mock_svc = Mock()
    mock_svc.model_available = False
    mock_svc.add_entries = AsyncMock(return_value=["test-uuid-1"])
    with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
        resp = api_client.post("/api/v1/kb/entries", json=KB_ENTRY_PAYLOAD, headers=api_headers)
    assert resp.status_code == 503
    assert "知识库功能不可用" in resp.json().get("detail", "")


def test_get_entries(api_client, api_headers):
    mock_svc = Mock()
    mock_svc.model_available = True
    mock_svc.list_entries = Mock(
        return_value={
            "items": [
                {
                    "id": "test-uuid-1",
                    "field_name": "业绩报酬提取方式",
                    "field_value": "高水位法",
                    "snippet": "",
                    "source_job_id": "job-1",
                    "source_filename": "test.docx",
                    "created_at": "2026-06-02T10:00:00+00:00",
                }
            ],
            "total": 1,
        }
    )
    with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
        resp = api_client.get("/api/v1/kb/entries?page=2&page_size=10", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    mock_svc.list_entries.assert_called_once_with(field_name=None, page=2, page_size=10)


def test_get_entries_filter(api_client, api_headers):
    mock_svc = Mock()
    mock_svc.model_available = True
    mock_svc.list_entries = Mock(return_value={"items": [], "total": 0})
    with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
        resp = api_client.get(
            "/api/v1/kb/entries?field_name=业绩报酬提取方式&page=1&page_size=5",
            headers=api_headers,
        )
    assert resp.status_code == 200
    mock_svc.list_entries.assert_called_once_with(
        field_name="业绩报酬提取方式",
        page=1,
        page_size=5,
    )


def test_delete_entry(api_client, api_headers):
    entry_id = "11111111-1111-1111-1111-111111111111"
    mock_svc = Mock()
    mock_svc.model_available = True
    mock_svc.delete_entry = Mock()
    with patch("backend.app.api.routes.kb.get_kb_service", return_value=mock_svc):
        resp = api_client.delete(f"/api/v1/kb/entries/{entry_id}", headers=api_headers)
    assert resp.status_code == 204
    mock_svc.delete_entry.assert_called_once_with(entry_id)
