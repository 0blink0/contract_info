from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.export.pipeline import export_xlsx
from backend.app.export.validate_export import merge_export_warnings
from backend.app.models.contract_file import ContractFile


def persist_export(file_id: uuid.UUID) -> tuple[str, str, str, str]:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        if not record.extraction_result:
            raise ValueError("extraction_result empty — run extract --persist first")

        record.status = "exporting"
        session.commit()

        try:
            product_path, fee_path, lock_path, share_path, export_warnings = export_xlsx(
                record.extraction_result, file_id
            )
            record.product_xlsx_path = product_path
            record.fee_xlsx_path = fee_path
            record.lock_xlsx_path = lock_path
            record.share_xlsx_path = share_path
            from backend.app.extract.schemas import ExtractionWarning

            warn_objs = [ExtractionWarning.model_validate(w) for w in export_warnings]
            record.extraction_warnings = merge_export_warnings(
                record.extraction_warnings, warn_objs
            )
            record.status = "exported"
            record.error_message = None
            session.commit()
            return product_path, fee_path, lock_path, share_path
        except Exception as exc:
            session.rollback()
            row = session.get(ContractFile, file_id)
            if row:
                row.status = "export_failed"
                row.error_message = str(exc)
                session.commit()
            raise
    finally:
        session.close()


def export_from_json(
    json_path: str, file_id: uuid.UUID | None = None
) -> tuple[str, str, str, str, list]:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    extraction = data.get("extraction") or data
    fid = file_id or uuid.uuid4()
    product, fee, lock, share, warnings = export_xlsx(extraction, fid)
    return product, fee, lock, share, warnings


def export_from_file_id(file_id: uuid.UUID) -> tuple[str, str, str, str, list]:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None or not record.extraction_result:
            raise ValueError(f"No extraction_result for {file_id}")
        return export_xlsx(record.extraction_result, file_id)
    finally:
        session.close()
