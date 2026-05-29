from __future__ import annotations

import uuid
from pathlib import Path

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select

from backend.app.api.deps import verify_api_key
from backend.app.api.schemas import (
    DeleteJobResponse,
    FeeSectionUpdate,
    JobDetailResponse,
    JobConcurrencyResponse,
    JobListItem,
    JobListResponse,
    JobPreviewResponse,
    JobPreviewSectionResponse,
    JobPreviewUpdateRequest,
    LockSectionUpdate,
    PreviewSection,
    ProductSectionUpdate,
    CrmHandoffItem,
    PathBResponse,
    PathBSnippetRow,
    ProductPreviewItem,
    ShareSectionUpdate,
    SubscriptionSectionUpdate,
    TableVerificationResponse,
    ValidationItemResponse,
    ValidationResponse,
    VerificationRow,
    RunResponse,
    warnings_from_jsonb,
)
from backend.app.services.preview_service import PREVIEW_STATUSES
from backend.app.services.delete_service import JobDeleteBusyError, delete_job_record
from backend.app.services.preview_edit_service import (
    apply_preview_edits,
    apply_section_preview_edits,
)
from backend.app.services.preview_service import get_job_preview, slice_preview
from backend.app.config import data_dir, exports_dir
from backend.app.extract.path_b_crm import build_crm_handoff
from backend.app.export.review_workbook import build_review_workbook
from backend.app.validate.field_labels import label_for_path_b_snippet
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.services.job_runner_service import get_runner
from backend.app.services.verification_service import (
    build_verification_rows,
    page_no_available,
)
from backend.app.services.pipeline_service import (
    PipelineBusyError,
    PipelineCompleteError,
    PipelineNotRunnableError,
    assert_can_run,
    count_in_progress,
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
    full = (data_dir() / rel_path).resolve()
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


@router.get("/concurrency", response_model=JobConcurrencyResponse)
def get_job_concurrency() -> JobConcurrencyResponse:
    return JobConcurrencyResponse(active=count_in_progress(), max=3)


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
    return _preview_response_from_data(data)


def _preview_response_from_data(data: dict) -> JobPreviewResponse:
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


def _section_response_from_data(data: dict, section: PreviewSection) -> JobPreviewSectionResponse:
    sliced = slice_preview(data, section)
    return JobPreviewSectionResponse(
        job_id=sliced["job_id"],
        section=section,
        source=sliced["source"],
        product_rows=[ProductPreviewItem.model_validate(r) for r in sliced.get("product_rows") or []]
        if sliced.get("product_rows") is not None
        else None,
        fee_columns=sliced.get("fee_columns"),
        fee_rows=sliced.get("fee_rows"),
        lock_columns=sliced.get("lock_columns"),
        lock_rows=sliced.get("lock_rows"),
        share_columns=sliced.get("share_columns"),
        share_rows=sliced.get("share_rows"),
        subscription_columns=sliced.get("subscription_columns"),
        subscription_rows=sliced.get("subscription_rows"),
    )


@router.get("/{job_id}/preview/{section}", response_model=JobPreviewSectionResponse)
def preview_job_section(job_id: uuid.UUID, section: PreviewSection) -> JobPreviewSectionResponse:
    try:
        data = get_job_preview(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _section_response_from_data(data, section)


_SECTION_UPDATE_MODELS: dict[PreviewSection, type] = {
    "product-elements": ProductSectionUpdate,
    "fee-rates": FeeSectionUpdate,
    "lock-periods": LockSectionUpdate,
    "share-classes": ShareSectionUpdate,
    "subscription-fee-rates": SubscriptionSectionUpdate,
}


@router.put("/{job_id}/preview/{section}", response_model=JobPreviewSectionResponse)
def update_job_section_preview(
    job_id: uuid.UUID,
    section: PreviewSection,
    body: dict[str, Any] = Body(...),
) -> JobPreviewSectionResponse:
    model_cls = _SECTION_UPDATE_MODELS[section]
    parsed = model_cls.model_validate(body)
    try:
        data = apply_section_preview_edits(job_id, section, parsed.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _section_response_from_data(data, section)


@router.put("/{job_id}/preview", response_model=JobPreviewResponse)
def update_job_preview(
    job_id: uuid.UUID,
    body: JobPreviewUpdateRequest,
) -> JobPreviewResponse:
    try:
        data = apply_preview_edits(job_id, body.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _preview_response_from_data(data)


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
def run_job(job_id: uuid.UUID) -> RunResponse:
    record = _get_record(job_id)
    try:
        assert_can_run(record.status)
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PipelineCompleteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PipelineNotRunnableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if count_in_progress() >= 3:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "已有 3 个任务正在处理，请稍后再试",
                "active_count": 3,
            },
        )

    get_runner().submit(job_id)
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


@router.get("/{job_id}/download/review-report")
def download_review_report(job_id: uuid.UUID) -> Response:
    """下载人工核对报告（路径A字段 + 路径B业绩报酬CRM）。"""
    record = _get_record(job_id)
    if record.status not in PREVIEW_STATUSES:
        raise HTTPException(status_code=409, detail="Job not extracted yet")

    extraction = getattr(record, "extraction_result", None) or {}
    product_elements: dict = extraction.get("product_elements") or {}
    fund_name = ""
    fe = product_elements.get("基金全称")
    if fe:
        fund_name = str(fe.get("value") if isinstance(fe, dict) else getattr(fe, "value", "")) or ""

    path_b_raw = getattr(record, "path_b_json", None) or {}
    perf = path_b_raw.get("performance_fee") or {}
    fees_ctx = str(perf.get("summary") or "")
    for t in perf.get("tiers") or []:
        if isinstance(t, dict) and t.get("description"):
            fees_ctx += " " + str(t["description"])

    handoff = build_crm_handoff(path_b_raw, fees_context=fees_ctx)
    snippets = path_b_raw.get("source_snippets") or {}
    snippet_rows = [
        {"path": p, "label": label_for_path_b_snippet(p, path_b_raw), "text": str(t)}
        for p, t in sorted(snippets.items())
        if t and str(t).strip()
    ]

    content = build_review_workbook(
        fund_name=fund_name or str(record.id)[:8],
        crm_rows=handoff,
        snippet_rows=snippet_rows,
        product_elements=product_elements,
        raw_sections=path_b_raw.get("raw_sections") or {},
    )
    safe_name = (fund_name or str(record.id)[:8]).replace("/", "_")[:40]
    return Response(
        content=content,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_核对报告.xlsx"'},
    )


@router.get("/{job_id}/verification/{table_key}", response_model=TableVerificationResponse)
def get_table_verification(
    job_id: uuid.UUID, table_key: PreviewSection
) -> TableVerificationResponse:
    record = _get_record(job_id)
    if record.status not in PREVIEW_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Job not extracted yet",
        )
    raw_rows = build_verification_rows(record, table_key)
    rows = [VerificationRow.model_validate(r) for r in raw_rows]
    return TableVerificationResponse(
        job_id=record.id,
        table_key=table_key,
        rows=rows,
        page_no_available=page_no_available(raw_rows),
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
        raw_sections=raw.get("raw_sections") or {},
    )
