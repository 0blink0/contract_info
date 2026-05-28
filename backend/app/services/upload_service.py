from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.config import uploads_dir, data_dir
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile


def validate_docx_filename(filename: str) -> None:
    name = (filename or "").strip()
    if not name.lower().endswith(".docx"):
        raise ValueError("Only .docx files are accepted")


def persist_upload(content: bytes, filename: str) -> uuid.UUID:
    validate_docx_filename(filename)

    file_id = uuid.uuid4()
    dest_dir = uploads_dir() / str(file_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / Path(filename).name
    dest_file.write_bytes(content)

    storage_path = str(dest_file.relative_to(data_dir())).replace("\\", "/")
    record = ContractFile(
        id=file_id,
        filename=Path(filename).name,
        status="pending",
        storage_path=storage_path,
    )

    session = SessionLocal()
    try:
        session.add(record)
        session.commit()
        return file_id
    finally:
        session.close()
