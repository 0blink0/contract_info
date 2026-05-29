import uuid
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.preview_edit_service import apply_preview_edits


def test_apply_preview_edits_updates_product_and_reexports():
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="exported",
        product_xlsx_path="exports/x/product_elements.xlsx",
        fee_xlsx_path=None,
        lock_xlsx_path=None,
        share_xlsx_path=None,
        subscription_xlsx_path=None,
        extraction_result={
            "product_elements": {"基金全称": {"value": "旧名称"}},
            "fee_rates": [],
            "lock_periods": [],
            "share_classes": [],
            "subscription_fees": [],
        },
    )

    class FakeSession:
        def get(self, _model, _id):
            return record

        def commit(self):
            return None

        def close(self):
            return None

    payload = {
        "product_rows": [{"field": "基金全称", "value": "新名称"}],
    }

    with (
        patch("backend.app.db.session.SessionLocal", return_value=FakeSession()),
        patch("backend.app.services.preview_edit_service.persist_export") as mock_export,
        patch(
            "backend.app.services.preview_service.build_job_preview",
            return_value={"job_id": job_id, "source": "xlsx", "product_rows": payload["product_rows"]},
        ),
    ):
        apply_preview_edits(job_id, payload)

    assert record.extraction_result["product_elements"]["基金全称"]["value"] == "新名称"
    assert record.extraction_result["fee_rates"] == []
    mock_export.assert_called_once_with(job_id)


def test_section_put_fee_does_not_clear_lock():
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="exported",
        extraction_result={
            "product_elements": {},
            "fee_rates": [{"管理费率": "1%"}],
            "lock_periods": [{"份额类别": "A", "锁定期": "12个月"}],
            "share_classes": [],
            "subscription_fees": [],
        },
    )

    class FakeSession:
        def get(self, _model, _id):
            return record

        def commit(self):
            return None

        def close(self):
            return None

    lock_len_before = len(record.extraction_result["lock_periods"])

    with (
        patch("backend.app.db.session.SessionLocal", return_value=FakeSession()),
        patch("backend.app.services.preview_edit_service.persist_export"),
        patch(
            "backend.app.services.preview_service.build_job_preview",
            return_value={"job_id": job_id, "source": "extraction"},
        ),
    ):
        from backend.app.services.preview_edit_service import apply_section_preview_edits

        apply_section_preview_edits(
            job_id,
            "fee-rates",
            {"fee_rows": [{"管理费率": "2%"}]},
        )

    assert len(record.extraction_result["lock_periods"]) == lock_len_before


def test_full_put_omitted_fields_unchanged():
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="exported",
        extraction_result={
            "product_elements": {"基金全称": {"value": "旧"}},
            "fee_rates": [{"x": "1"}],
            "lock_periods": [],
            "share_classes": [],
            "subscription_fees": [],
        },
    )

    class FakeSession:
        def get(self, _model, _id):
            return record

        def commit(self):
            return None

        def close(self):
            return None

    fee_len = len(record.extraction_result["fee_rates"])

    with (
        patch("backend.app.db.session.SessionLocal", return_value=FakeSession()),
        patch("backend.app.services.preview_edit_service.persist_export"),
        patch(
            "backend.app.services.preview_service.build_job_preview",
            return_value={"job_id": job_id, "source": "extraction"},
        ),
    ):
        apply_preview_edits(
            job_id,
            {"product_rows": [{"field": "基金全称", "value": "新"}]},
        )

    assert len(record.extraction_result["fee_rates"]) == fee_len
