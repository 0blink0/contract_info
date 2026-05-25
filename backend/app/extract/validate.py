from __future__ import annotations

import json
from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.extract.schemas import ExtractionResult, ExtractionWarning

DICTS_DIR = PROJECT_ROOT / "dicts"

_ENUM_CHECKS: dict[str, str] = {
    "销售机构信息": "销售机构及名称对应表",
    "业绩比较基准": "业绩比较基准指数表",
}


def _load_dict_records(slug_part: str) -> list[dict[str, str]]:
    if not DICTS_DIR.is_dir():
        return []
    for path in DICTS_DIR.glob("*.json"):
        if slug_part in path.stem or slug_part in path.name:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    return []


def _known_values(records: list[dict[str, str]]) -> set[str]:
    known: set[str] = set()
    for row in records:
        for v in row.values():
            if v:
                known.add(v.strip())
    return known


def validate_enums(result: ExtractionResult) -> list[ExtractionWarning]:
    warnings: list[ExtractionWarning] = []
    for field_name, slug in _ENUM_CHECKS.items():
        fv = result.product_elements.get(field_name)
        if not fv or not fv.value:
            continue
        records = _load_dict_records(slug)
        if not records:
            continue
        known = _known_values(records)
        val = str(fv.value).strip()
        if known and val not in known:
            warnings.append(
                ExtractionWarning(
                    field=field_name,
                    code="enum_unknown",
                    message=f"值「{val}」不在字典 {slug} 中",
                    suggestion=val,
                )
            )
    return warnings
