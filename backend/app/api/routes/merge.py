from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from backend.app.api.deps import verify_api_key
from backend.app.config import data_dir
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.services.merge_service import (
    TABLE_TYPE_LABELS,
    append_to_merge,
    create_merge,
    delete_all_merges,
    delete_merge,
    get_merge,
    get_merge_file_path,
    get_merge_preview,
    list_merges,
    merge_xlsx_files,
)

router = APIRouter(
    prefix="/merge",
    tags=["merge"],
    dependencies=[Depends(verify_api_key)],
)

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_TABLE_PATH_ATTR: dict[str, str] = {
    "product-elements": "product_xlsx_path",
    "fee-rates": "fee_xlsx_path",
    "lock-periods": "lock_xlsx_path",
    "share-classes": "share_xlsx_path",
    "subscription-fee-rates": "subscription_xlsx_path",
}

VALID_TABLE_TYPES = frozenset(_TABLE_PATH_ATTR.keys())


class CreateMergeRequest(BaseModel):
    job_ids: list[str]
    table_type: str
    name: str = ""


class MergeSourceJob(BaseModel):
    job_id: str
    filename: str


class MergeRecordResponse(BaseModel):
    id: str
    name: str
    table_type: str
    table_type_label: str
    source_jobs: list[MergeSourceJob]
    merged_at: str
    row_count: int
    columns: list[str]


class MergePreviewResponse(BaseModel):
    id: str
    columns: list[str]
    rows: list[dict[str, str]]


class AppendMergeRequest(BaseModel):
    job_ids: list[str]


class DeleteMergeResponse(BaseModel):
    id: str


def _record_to_response(r: dict) -> MergeRecordResponse:
    return MergeRecordResponse(
        id=r["id"],
        name=r.get("name", ""),
        table_type=r.get("table_type", ""),
        table_type_label=TABLE_TYPE_LABELS.get(r.get("table_type", ""), r.get("table_type", "")),
        source_jobs=[MergeSourceJob(**sj) for sj in (r.get("source_jobs") or [])],
        merged_at=r.get("merged_at", ""),
        row_count=r.get("row_count", 0),
        columns=r.get("columns") or [],
    )


@router.post("", response_model=MergeRecordResponse, status_code=201)
def create_merge_endpoint(body: CreateMergeRequest) -> MergeRecordResponse:
    if body.table_type not in VALID_TABLE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid table_type. Must be one of: {sorted(VALID_TABLE_TYPES)}",
        )
    if not body.job_ids:
        raise HTTPException(status_code=422, detail="job_ids must not be empty")

    path_attr = _TABLE_PATH_ATTR[body.table_type]
    session = SessionLocal()
    try:
        paths: list[Path] = []
        source_jobs: list[dict] = []

        for jid_str in body.job_ids:
            try:
                jid = uuid.UUID(jid_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid job_id: {jid_str}")

            record = session.get(ContractFile, jid)
            if record is None:
                raise HTTPException(status_code=404, detail=f"Job not found: {jid_str}")
            if record.status != "exported":
                raise HTTPException(
                    status_code=409,
                    detail=f"Job {jid_str} ({record.filename}) is not in 'exported' state",
                )

            rel_path: str | None = getattr(record, path_attr, None)
            if not rel_path:
                raise HTTPException(
                    status_code=409,
                    detail=f"Job {jid_str} has no {body.table_type} export file",
                )

            full_path = (data_dir() / rel_path).resolve()
            if not full_path.is_file():
                raise HTTPException(
                    status_code=409,
                    detail=f"Export file missing for job {jid_str}",
                )

            paths.append(full_path)
            source_jobs.append({"job_id": jid_str, "filename": record.filename})
    finally:
        session.close()

    xlsx_bytes, columns, preview_rows = merge_xlsx_files(paths, body.table_type)

    record_dict = create_merge(
        job_ids=body.job_ids,
        table_type=body.table_type,
        source_jobs=source_jobs,
        xlsx_bytes=xlsx_bytes,
        columns=columns,
        row_count=len(preview_rows),
        name=body.name,
    )
    return _record_to_response(record_dict)


@router.post("/{merge_id}/append", response_model=MergeRecordResponse)
def append_merge_endpoint(merge_id: str, body: AppendMergeRequest) -> MergeRecordResponse:
    """向已有合并记录中追加新的任务文件。"""
    existing = get_merge(merge_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Merge record not found")

    table_type = existing.get("table_type", "")
    if table_type not in VALID_TABLE_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown table_type: {table_type}")

    if not body.job_ids:
        raise HTTPException(status_code=422, detail="job_ids must not be empty")

    path_attr = _TABLE_PATH_ATTR[table_type]
    existing_job_ids = {sj.get("job_id") for sj in (existing.get("source_jobs") or [])}

    session = SessionLocal()
    try:
        new_paths: list[Path] = []
        new_source_jobs: list[dict] = []

        for jid_str in body.job_ids:
            if jid_str in existing_job_ids:
                raise HTTPException(
                    status_code=409,
                    detail=f"Job {jid_str} is already included in this merge",
                )
            try:
                jid = uuid.UUID(jid_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid job_id: {jid_str}")

            record = session.get(ContractFile, jid)
            if record is None:
                raise HTTPException(status_code=404, detail=f"Job not found: {jid_str}")
            if record.status != "exported":
                raise HTTPException(
                    status_code=409,
                    detail=f"Job {jid_str} ({record.filename}) is not in 'exported' state",
                )

            rel_path: str | None = getattr(record, path_attr, None)
            if not rel_path:
                raise HTTPException(
                    status_code=409,
                    detail=f"Job {jid_str} has no {table_type} export file",
                )

            full_path = (data_dir() / rel_path).resolve()
            if not full_path.is_file():
                raise HTTPException(
                    status_code=409,
                    detail=f"Export file missing for job {jid_str}",
                )

            new_paths.append(full_path)
            new_source_jobs.append({"job_id": jid_str, "filename": record.filename})
    finally:
        session.close()

    updated = append_to_merge(merge_id, new_paths, new_source_jobs)
    if not updated:
        raise HTTPException(status_code=404, detail="Merge record not found")
    return _record_to_response(updated)


@router.get("", response_model=list[MergeRecordResponse])
def list_merges_endpoint() -> list[MergeRecordResponse]:
    return [_record_to_response(r) for r in list_merges()]


@router.get("/{merge_id}/preview", response_model=MergePreviewResponse)
def preview_merge_endpoint(merge_id: str) -> MergePreviewResponse:
    result = get_merge_preview(merge_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Merge record not found")
    return MergePreviewResponse(**result)


@router.get("/{merge_id}/download")
def download_merge_endpoint(merge_id: str) -> Response:
    record = get_merge(merge_id)
    if not record:
        raise HTTPException(status_code=404, detail="Merge record not found")
    fp = get_merge_file_path(merge_id)
    if not fp:
        raise HTTPException(status_code=404, detail="Merged file not found on disk")
    table_label = TABLE_TYPE_LABELS.get(record.get("table_type", ""), "merged")
    safe_name = table_label.replace("/", "_")[:30]
    return FileResponse(
        fp,
        media_type=XLSX_MEDIA,
        filename=f"{safe_name}_合并.xlsx",
    )


@router.delete("/all", response_model=dict)
def delete_all_merges_endpoint() -> dict:
    count = delete_all_merges()
    return {"deleted": count}


@router.delete("/{merge_id}", response_model=DeleteMergeResponse)
def delete_merge_endpoint(merge_id: str) -> DeleteMergeResponse:
    if not delete_merge(merge_id):
        raise HTTPException(status_code=404, detail="Merge record not found")
    return DeleteMergeResponse(id=merge_id)
