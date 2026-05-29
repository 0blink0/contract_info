from unittest.mock import patch


def test_get_concurrency_returns_active_and_max(api_client, api_headers):
    with patch("backend.app.api.routes.jobs.count_in_progress", return_value=2):
        response = api_client.get("/api/v1/jobs/concurrency", headers=api_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["active"] == 2
    assert body["max"] == 3


def test_get_concurrency_when_idle(api_client, api_headers):
    with patch("backend.app.api.routes.jobs.count_in_progress", return_value=0):
        response = api_client.get("/api/v1/jobs/concurrency", headers=api_headers)
    assert response.status_code == 200
    assert response.json()["active"] == 0
