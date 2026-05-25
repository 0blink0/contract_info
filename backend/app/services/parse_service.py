import shutil
import uuid
from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.db.session import SessionLocal
from backend.app.models.contract_file import ContractFile
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict, outline_preview_from_document


def persist_parse(file_path: str) -> uuid.UUID:
    source = Path(file_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(file_path)

    file_id = uuid.uuid4()
    dest_dir = PROJECT_ROOT / "uploads" / str(file_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / source.name
    shutil.copy2(source, dest_file)

    storage_path = str(dest_file.relative_to(PROJECT_ROOT)).replace("\\", "/")
    record = ContractFile(
        id=file_id,
        filename=source.name,
        status="parsing",
        storage_path=storage_path,
    )

    session = SessionLocal()
    try:
        session.add(record)
        session.commit()
        document = parse_docx(str(dest_file))
        record.parse_json = document_to_dict(document)
        record.outline_preview = outline_preview_from_document(document)
        record.status = "parsed"
        record.error_message = None
        session.commit()
        return file_id
    except Exception as exc:
        session.rollback()
        failed = session.get(ContractFile, file_id)
        if failed is None:
            failed = ContractFile(
                id=file_id,
                filename=source.name,
                status="failed",
                storage_path=storage_path,
                error_message=str(exc),
            )
            session.add(failed)
        else:
            failed.status = "failed"
            failed.error_message = str(exc)
        session.commit()
        raise
    finally:
        session.close()
