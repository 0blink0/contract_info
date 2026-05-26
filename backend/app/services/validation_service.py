from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.extract.schemas import ExtractionWarning
from backend.app.models.contract_file import ContractFile
from backend.app.validate.llm_validator import run_llm_validation_sync
from backend.app.validate.schemas import ValidationResult


def _append_warning(
    warnings: list[Any],
    *,
    field: str,
    code: str,
    message: str,
    suggestion: str | None = None,
) -> list[Any]:
    out = list(warnings) if warnings else []
    out.append(
        ExtractionWarning(
            field=field,
            code=code,
            message=message,
            suggestion=suggestion,
        ).model_dump(exclude_none=True)
    )
    return out


def _apply_validation_warnings(
    warnings: list[Any] | None,
    result: ValidationResult,
) -> list[Any]:
    out = list(warnings) if warnings else []
    if result.skipped:
        return _append_warning(
            out,
            field="_validation",
            code="validation_skipped",
            message="LLM validation skipped (API not configured)",
        )
    fail_n = result.summary.get("fail", 0)
    warn_n = result.summary.get("warn", 0)
    if fail_n or warn_n:
        return _append_warning(
            out,
            field="_validation",
            code="validation_issues",
            message=f"LLM validation: {fail_n} fail, {warn_n} warn",
            suggestion="See GET /jobs/{id}/validation for details",
        )
    return out


def persist_validation(
    file_id: uuid.UUID,
    session: Session | None = None,
) -> dict | None:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        if not record.extraction_result:
            return None

        try:
            result = run_llm_validation_sync(
                record.extraction_result,
                record.path_b_json,
                record.parse_json or {},
            )
            record.extraction_warnings = _apply_validation_warnings(
                record.extraction_warnings,
                result,
            )
        except Exception as exc:
            result = ValidationResult(skipped=True, items=[])
            result.compute_summary()
            record.extraction_warnings = _append_warning(
                record.extraction_warnings or [],
                field="_validation",
                code="validation_failed",
                message=f"LLM validation failed: {exc}"[:500],
                suggestion="抽取结果已保留，可重试或检查 LLM 响应格式",
            )
        record.validation_result = result.model_dump()
        if own_session:
            session.commit()
        return record.validation_result
    finally:
        if own_session:
            session.close()
