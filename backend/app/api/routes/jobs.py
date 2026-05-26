from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.app.api.deps import verify_api_key
from backend.app.api.schemas import (
    JobDetailResponse,
    JobListItem,
    JobListResponse,
    JobPreviewResponse,
    ProductPreviewItem,
    RunResponse,
    warnings_from_jsonb,
)
from backend.app.services.preview_service import get_job_preview
from backend.app.config import PROJECT_ROOT, exports_dir
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


def _record_to_detail(record: ContractFile) -> JobDetailResponse:
    warnings = warnings_from_jsonb(record.extraction_warnings)
    outline = record.outline_preview
    return JobDetailResponse(
        job_id=record.id,
        filename=record.filename,
        status=record.status,
        error_message=record.error_message,
        product_xlsx_path=record.product_xlsx_path,
        fee_xlsx_path=record.fee_xlsx_path,
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
def list_jobs(limit: int = Query(20, ge=1, le=50)) -> JobListResponse:
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
    )


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
