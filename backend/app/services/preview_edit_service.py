"""Apply UI preview edits to extraction_result and regenerate export xlsx files."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Callable

from backend.app.api.schemas import PreviewSection
from backend.app.export.column_map import (
    extraction_key_for_fee_header,
    extraction_key_for_subscription_header,
)
from backend.app.services.export_service import persist_export
from backend.app.services.preview_service import PREVIEW_STATUSES, SNIPPET_DISPLAY


def _apply_product_edits(
    extraction: dict[str, Any], product_rows: list[dict[str, Any]]
) -> None:
    elements = extraction.setdefault("product_elements", {})
    if not isinstance(elements, dict):
        extraction["product_elements"] = elements = {}
    for row in product_rows:
        field = str(row.get("field") or "").strip()
        if not field:
            continue
        value = row.get("value")
        text = "" if value is None else str(value).strip()
        current = elements.get(field)
        if isinstance(current, dict):
            current["value"] = text
        else:
            elements[field] = {"value": text}


def _apply_list_table_edits(
    extraction: dict[str, Any],
    *,
    list_key: str,
    preview_rows: list[dict[str, Any]],
    label_to_key: Callable[[str], str],
) -> None:
    existing = extraction.get(list_key) or []
    if not isinstance(existing, list):
        existing = []
    updated: list[dict[str, Any]] = []
    for i, prow in enumerate(preview_rows):
        if not isinstance(prow, dict):
            continue
        base: dict[str, Any] = deepcopy(existing[i]) if i < len(existing) and isinstance(existing[i], dict) else {}
        for label, val in prow.items():
            if label == SNIPPET_DISPLAY:
                continue
            key = label_to_key(str(label))
            if val is None or (isinstance(val, str) and not val.strip()):
                base.pop(key, None)
            else:
                base[key] = str(val).strip()
        if base:
            updated.append(base)
    extraction[list_key] = updated


def apply_section_preview_edits(
    file_id: uuid.UUID,
    section: PreviewSection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile
    from backend.app.services.preview_service import build_job_preview

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        if record.status not in PREVIEW_STATUSES:
            raise ValueError(f"Cannot edit preview for status: {record.status}")
        if not record.extraction_result:
            raise ValueError("extraction_result empty — run extract first")

        extraction = deepcopy(record.extraction_result)
        if section == "product-elements":
            rows = payload.get("product_rows")
            if rows is not None:
                _apply_product_edits(extraction, rows)
        elif section == "fee-rates":
            if payload.get("fee_rows") is not None:
                _apply_list_table_edits(
                    extraction,
                    list_key="fee_rates",
                    preview_rows=payload["fee_rows"],
                    label_to_key=extraction_key_for_fee_header,
                )
        elif section == "lock-periods":
            if payload.get("lock_rows") is not None:
                _apply_list_table_edits(
                    extraction,
                    list_key="lock_periods",
                    preview_rows=payload["lock_rows"],
                    label_to_key=lambda label: label,
                )
        elif section == "share-classes":
            if payload.get("share_rows") is not None:
                _apply_list_table_edits(
                    extraction,
                    list_key="share_classes",
                    preview_rows=payload["share_rows"],
                    label_to_key=lambda label: label,
                )
        elif section == "subscription-fee-rates":
            if payload.get("subscription_rows") is not None:
                _apply_list_table_edits(
                    extraction,
                    list_key="subscription_fees",
                    preview_rows=payload["subscription_rows"],
                    label_to_key=extraction_key_for_subscription_header,
                )

        record.extraction_result = extraction
        session.commit()

        persist_export(file_id)

        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        return build_job_preview(record)
    finally:
        session.close()


def apply_preview_edits(
    file_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile
    from backend.app.services.preview_service import build_job_preview

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        if record.status not in PREVIEW_STATUSES:
            raise ValueError(f"Cannot edit preview for status: {record.status}")
        if not record.extraction_result:
            raise ValueError("extraction_result empty — run extract first")

        extraction = deepcopy(record.extraction_result)
        product_rows = payload.get("product_rows")
        if product_rows is not None:
            _apply_product_edits(extraction, product_rows)
        fee_rows = payload.get("fee_rows")
        if fee_rows is not None:
            _apply_list_table_edits(
                extraction,
                list_key="fee_rates",
                preview_rows=fee_rows,
                label_to_key=extraction_key_for_fee_header,
            )
        lock_rows = payload.get("lock_rows")
        if lock_rows is not None:
            _apply_list_table_edits(
                extraction,
                list_key="lock_periods",
                preview_rows=lock_rows,
                label_to_key=lambda label: label,
            )
        share_rows = payload.get("share_rows")
        if share_rows is not None:
            _apply_list_table_edits(
                extraction,
                list_key="share_classes",
                preview_rows=share_rows,
                label_to_key=lambda label: label,
            )
        subscription_rows = payload.get("subscription_rows")
        if subscription_rows is not None:
            _apply_list_table_edits(
                extraction,
                list_key="subscription_fees",
                preview_rows=subscription_rows,
                label_to_key=extraction_key_for_subscription_header,
            )

        record.extraction_result = extraction
        session.commit()

        persist_export(file_id)

        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        return build_job_preview(record)
    finally:
        session.close()
