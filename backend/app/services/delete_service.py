from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from backend.app.config import uploads_dir, exports_dir
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.services.pipeline_service import IN_PROGRESS


class JobDeleteBusyError(Exception):
    pass


def delete_job_record(file_id: uuid.UUID) -> None:
    session = SessionLocal()
    try:
        record = session.get(ContractFile, file_id)
        if record is None:
            raise LookupError(f"contract_file not found: {file_id}")
        if record.status in IN_PROGRESS:
            raise JobDeleteBusyError(f"Job is in progress: {record.status}")

        session.delete(record)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    _remove_tree(uploads_dir() / str(file_id))
    _remove_tree(exports_dir() / str(file_id))


def _remove_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)
