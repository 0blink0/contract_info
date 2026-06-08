from unittest.mock import Mock, patch

import pytest


def test_init_creates_table(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("CTRX_MODELS_DIR", raising=False)

    with patch("lancedb.connect") as mock_connect:
        mock_db = Mock()
        mock_connect.return_value = mock_db
        mock_db.open_table.side_effect = Exception("missing")
        mock_db.create_table.return_value = Mock()

        from backend.app.services import kb_service

        kb_service._kb = None
        kb_service.init_kb_service()

        assert kb_service._kb is not None
        assert kb_service._kb.model_available is False


def test_model_unavailable_soft_degrade(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("CTRX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CTRX_MODELS_DIR", str(tmp_path / "nonexistent_models"))

    with patch("lancedb.connect") as mock_connect:
        mock_db = Mock()
        mock_connect.return_value = mock_db
        mock_db.open_table.side_effect = Exception("missing")
        mock_db.create_table.return_value = Mock()

        from backend.app.services import kb_service

        kb_service._kb = None
        kb_service.init_kb_service()

        assert kb_service._kb is not None
        assert kb_service._kb.model_available is False
