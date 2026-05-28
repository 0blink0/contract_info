from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.app.api.deps import verify_api_key
from backend.app.api.schemas import (
    DeleteJobResponse,
    JobDetailResponse,
    JobListItem,
    JobListResponse,
    JobPreviewResponse,
    CrmHandoffItem,
    PathBResponse,
    PathBSnippetRow,
    ProductPreviewItem,
    ValidationItemResponse,
    ValidationResponse,
    RunResponse,
    warnings_from_jsonb,
)
from backend.app.services.preview_service import PREVIEW_STATUSES
from backend.app.services.delete_service import JobDeleteBusyError, delete_job_record
from backend.app.services.preview_service import get_job_preview
from backend.app.config import PROJECT_ROOT, exports_dir
from backend.app.extract.path_b_crm import build_crm_handoff
from backend.app.validate.field_labels import label_for_path_b_snippet
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.services.pipeline_service import (
    PipelineBusyError,
    PipelineCompleteError,
    PipelineNotRunnableError,
    assert_can_run,
    run_pipeline,
)

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _get_record(job_id: uuid.UUID) -> ContractFile:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")
        session.expunge(record)
        return record
    finally:
        session.close()


def _validation_counts(record: ContractFile) -> tuple[bool, int, int]:
    raw = getattr(record, "validation_result", None)
    if not raw or not isinstance(raw, dict):
        return False, 0, 0
    summary = raw.get("summary") or {}
    fail_n = int(summary.get("fail") or 0)
    warn_n = int(summary.get("warn") or 0)
    return True, fail_n, warn_n


def _record_to_detail(record: ContractFile) -> JobDetailResponse:
    warnings = warnings_from_jsonb(record.extraction_warnings)
    outline = record.outline_preview
    val_available, fail_n, warn_n = _validation_counts(record)
    return JobDetailResponse(
        job_id=record.id,
        filename=record.filename,
        status=record.status,
        error_message=record.error_message,
        product_xlsx_path=record.product_xlsx_path,
        fee_xlsx_path=record.fee_xlsx_path,
        lock_xlsx_path=getattr(record, "lock_xlsx_path", None),
        share_xlsx_path=getattr(record, "share_xlsx_path", None),
        subscription_xlsx_path=getattr(record, "subscription_xlsx_path", None),
        path_b_available=bool(getattr(record, "path_b_json", None)),
        validation_available=val_available,
        validation_fail_count=fail_n,
        validation_warn_count=warn_n,
        extraction_warnings=warnings,
        extraction_warnings_count=len(warnings),
        outline_preview_count=len(outline) if isinstance(outline, list) else None,
    )


def _resolve_export_path(rel_path: str | None) -> Path:
    if not rel_path:
        raise HTTPException(status_code=404, detail="Export file path not set")
    full = (PROJECT_ROOT / rel_path).resolve()
    root = exports_dir().resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid export path") from None
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Export file missing")
    return full


@router.get("", response_model=JobListResponse)
def list_jobs(limit: int = Query(50, ge=1, le=200)) -> JobListResponse:
    session = SessionLocal()
    try:
        stmt = (
            select(ContractFile)
            .order_by(ContractFile.created_at.desc())
            .limit(limit)
        )
        rows = session.scalars(stmt).all()
        items = [
            JobListItem(
                job_id=row.id,
                filename=row.filename,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return JobListResponse(items=items)
    finally:
        session.close()


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: uuid.UUID) -> JobDetailResponse:
    record = _get_record(job_id)
    return _record_to_detail(record)


@router.get("/{job_id}/preview", response_model=JobPreviewResponse)
def preview_job(job_id: uuid.UUID) -> JobPreviewResponse:
    try:
        data = get_job_preview(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JobPreviewResponse(
        job_id=data["job_id"],
        source=data["source"],
        product_rows=[ProductPreviewItem.model_validate(r) for r in data["product_rows"]],
        fee_columns=data["fee_columns"],
        fee_rows=data["fee_rows"],
        lock_columns=data["lock_columns"],
        lock_rows=data["lock_rows"],
        share_columns=data["share_columns"],
        share_rows=data["share_rows"],
        subscription_columns=data.get("subscription_columns") or [],
        subscription_rows=data.get("subscription_rows") or [],
    )


@router.delete("/{job_id}", response_model=DeleteJobResponse)
def delete_job(job_id: uuid.UUID) -> DeleteJobResponse:
    try:
        delete_job_record(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobDeleteBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DeleteJobResponse(job_id=job_id)


@router.post("/{job_id}/run", response_model=RunResponse, status_code=202)
def run_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    record = _get_record(job_id)
    try:
        assert_can_run(record.status)
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PipelineCompleteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PipelineNotRunnableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    background_tasks.add_task(run_pipeline, job_id)
    return RunResponse(job_id=job_id, status=record.status)


@router.get("/{job_id}/download/product-elements")
def download_product_elements(job_id: uuid.UUID) -> FileResponse:
    record = _get_record(job_id)
    if record.status != "exported":
        raise HTTPException(status_code=409, detail="Job not exported yet")
    path = _resolve_export_path(record.product_xlsx_path)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA,
        filename="product_elements.xlsx",
    )


@router.get("/{job_id}/download/fee-rates")
def download_fee_rates(job_id: uuid.UUID) -> FileResponse:
    record = _get_record(job_id)
    if record.status != "exported":
        raise HTTPException(status_code=409, detail="Job not exported yet")
    path = _resolve_export_path(record.fee_xlsx_path)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA,
        filename="fee_rates.xlsx",
    )


@router.get("/{job_id}/download/lock-periods")
def download_lock_periods(job_id: uuid.UUID) -> FileResponse:
    record = _get_record(job_id)
    if record.status != "exported":
        raise HTTPException(status_code=409, detail="Job not exported yet")
    path = _resolve_export_path(record.lock_xlsx_path)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA,
        filename="lock_periods.xlsx",
    )


@router.get("/{job_id}/download/share-classes")
def download_share_classes(job_id: uuid.UUID) -> FileResponse:
    record = _get_record(job_id)
    if record.status != "exported":
        raise HTTPException(status_code=409, detail="Job not exported yet")
    path = _resolve_export_path(record.share_xlsx_path)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA,
        filename="share_classes.xlsx",
    )


@router.get("/{job_id}/download/subscription-fee-rates")
def download_subscription_fee_rates(job_id: uuid.UUID) -> FileResponse:
    record = _get_record(job_id)
    if record.status != "exported":
        raise HTTPException(status_code=409, detail="Job not exported yet")
    path = _resolve_export_path(
        getattr(record, "subscription_xlsx_path", None)
    )
    return FileResponse(
        path,
        media_type=XLSX_MEDIA,
        filename="subscription_fee_rates.xlsx",
    )


@router.get("/{job_id}/validation", response_model=ValidationResponse)
def get_validation(job_id: uuid.UUID) -> ValidationResponse:
    record = _get_record(job_id)
    if record.status not in PREVIEW_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Job not extracted yet",
        )
    raw = getattr(record, "validation_result", None)
    if raw is None or not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Validation result not available")
    from backend.app.validate.field_labels import label_for_validation_field

    items_raw = raw.get("items") or []
    items: list[ValidationItemResponse] = []
    for entry in items_raw:
        if not isinstance(entry, dict):
            continue
        payload = dict(entry)
        if not payload.get("field_label"):
            payload["field_label"] = label_for_validation_field(
                str(payload.get("field") or ""),
                getattr(record, "extraction_result", None),
            )
        items.append(ValidationItemResponse.model_validate(payload))
    return ValidationResponse(
        job_id=record.id,
        validated_at=raw.get("validated_at"),
        model=raw.get("model"),
        skipped=bool(raw.get("skipped")),
        items=items,
        summary=raw.get("summary") or {},
    )


@router.get("/{job_id}/path-b", response_model=PathBResponse)
def get_path_b(job_id: uuid.UUID) -> PathBResponse:
    record = _get_record(job_id)
    if record.status not in PREVIEW_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Job not extracted yet",
        )
    raw = getattr(record, "path_b_json", None)
    if not raw or not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Path B JSON not available")
    perf = raw.get("performance_fee") or {}
    fees_ctx = str(perf.get("summary") or "")
    for t in perf.get("tiers") or []:
        if isinstance(t, dict) and t.get("description"):
            fees_ctx += " " + str(t["description"])
    handoff = build_crm_handoff(raw, fees_context=fees_ctx)
    snippets = raw.get("source_snippets") or {}
    snippet_rows = [
        PathBSnippetRow(
            path=path,
            label=label_for_path_b_snippet(path, raw),
            text=str(text),
        )
        for path, text in sorted(snippets.items())
        if text and str(text).strip()
    ]
    return PathBResponse(
        job_id=record.id,
        performance_fee=perf,
        open_day=raw.get("open_day") or {},
        source_snippets=snippets,
        source_snippet_rows=snippet_rows,
        crm_handoff=[CrmHandoffItem(**item) for item in handoff],
    )
