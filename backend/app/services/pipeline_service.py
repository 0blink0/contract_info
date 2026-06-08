from __future__ import annotations

import uuid

from sqlalchemy import asc, func, select

from backend.app.services.export_service import persist_export
from backend.app.services.extract_service import persist_extract
from backend.app.services.parse_service import parse_file_id

IN_PROGRESS = frozenset({"parsing", "extracting", "exporting"})


class PipelineBusyError(Exception):
    pass


class PipelineCompleteError(Exception):
    pass


class PipelineNotRunnableError(Exception):
    pass


def can_run(status: str) -> bool:
    if status in IN_PROGRESS:
        return False
    if status == "exported":
        return False
    return status in {
        "pending",
        "queued",
        "failed",
        "parsed",
        "extraction_failed",
        "extracted",
        "export_failed",
    }


def count_in_progress(session=None) -> int:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    own_session = session is None
    if own_session:
        session = SessionLocal()
    try:
        stmt = (
            select(func.count())
            .select_from(ContractFile)
            .where(ContractFile.status.in_(IN_PROGRESS))
        )
        return int(session.scalar(stmt) or 0)
    finally:
        if own_session:
            session.close()


def count_queued(session=None) -> int:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    own_session = session is None
    if own_session:
        session = SessionLocal()
    try:
        stmt = (
            select(func.count())
            .select_from(ContractFile)
            .where(ContractFile.status == "queued")
        )
        return int(session.scalar(stmt) or 0)
    finally:
        if own_session:
            session.close()


def get_next_queued_id(session=None) -> uuid.UUID | None:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    own_session = session is None
    if own_session:
        session = SessionLocal()
    try:
        stmt = (
            select(ContractFile)
            .where(ContractFile.status == "queued")
            .order_by(asc(ContractFile.created_at))
            .limit(1)
        )
        row = session.scalars(stmt).first()
        return row.id if row else None
    finally:
        if own_session:
            session.close()


def assert_can_run(status: str) -> None:
    if status in IN_PROGRESS:
        raise PipelineBusyError(f"Job is in progress: {status}")
    if status == "exported":
        raise PipelineCompleteError("Job already exported")
    if not can_run(status):
        raise PipelineNotRunnableError(f"Cannot run pipeline from status: {status}")


def run_pipeline(file_id: uuid.UUID) -> None:
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile

    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise ValueError(f"contract_file not found: {file_id}")
        status = record.status
    finally:
        session.close()

    assert_can_run(status)

    if status in ("pending", "queued", "failed"):
        parse_file_id(file_id)
        persist_extract(file_id)
        persist_export(file_id)
    elif status in ("parsed", "extraction_failed"):
        persist_extract(file_id)
        persist_export(file_id)
    elif status in ("extracted", "export_failed"):
        persist_export(file_id)
