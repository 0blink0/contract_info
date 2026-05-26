from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.export.pipeline import export_xlsx
from backend.app.extract.pipeline import extract_document_sync
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict


class LlmOff:
    available = False
    model_name = ""


@dataclass
class GoldenRunResult:
    extraction: dict[str, Any]
    product_path: Path
    fee_path: Path
    lock_path: Path
    share_path: Path
    subscription_path: Path
    warnings: list[Any]


def run_golden_pipeline(
    docx_path: Path,
    *,
    exports_root: Path,
    monkeypatch=None,
) -> GoldenRunResult:
    if monkeypatch is not None:
        monkeypatch.setattr(
            "backend.app.export.pipeline.exports_dir",
            lambda: exports_root,
        )
    doc = parse_docx(str(docx_path))
    document = document_to_dict(doc)
    result, warnings, _path_b = extract_document_sync(document, llm_client=LlmOff())  # type: ignore[arg-type]
    extraction = result.model_dump(mode="json")
    fid = uuid.uuid4()
    product_rel, fee_rel, lock_rel, share_rel, sub_rel, export_warnings = export_xlsx(
        extraction, fid
    )
    base = exports_root / str(fid)
    return GoldenRunResult(
        extraction=extraction,
        product_path=base / Path(product_rel).name,
        fee_path=base / Path(fee_rel).name,
        lock_path=base / Path(lock_rel).name,
        share_path=base / Path(share_rel).name,
        subscription_path=base / Path(sub_rel).name,
        warnings=list(warnings) + list(export_warnings),
    )
