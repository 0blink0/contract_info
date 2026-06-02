import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa

from backend.app.config import data_dir

logger = logging.getLogger(__name__)

KB_TABLE_NAME = "kb_entries"
VECTOR_DIM = 1024

_KB_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("field_name", pa.string()),
        pa.field("field_value", pa.string()),
        pa.field("snippet", pa.string()),
        pa.field("source_job_id", pa.string()),
        pa.field("source_filename", pa.string()),
        pa.field("created_at", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
    ]
)


class KbService:
    def __init__(self, table: Any) -> None:
        self._table = table
        self._model: Any = None

    def set_model(self, model: Any) -> None:
        self._model = model

    @property
    def model_available(self) -> bool:
        return self._model is not None

    def _build_embedding_text(self, field_name: str, field_value: str, snippet: str) -> str:
        return f"字段名：{field_name}\n字段值：{field_value}\n原文摘录：{snippet}"[:512]

    async def add_entries(self, items: list[dict[str, str]]) -> list[str]:
        if not self.model_available:
            raise RuntimeError("model_unavailable")

        texts = [
            self._build_embedding_text(
                field_name=item.get("field_name", ""),
                field_value=item.get("field_value", ""),
                snippet=item.get("snippet", ""),
            )
            for item in items
        ]
        vectors = await asyncio.to_thread(
            self._model.encode,
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        ids: list[str] = []
        rows: list[dict[str, Any]] = []
        for item, vector in zip(items, vectors):
            entry_id = str(uuid.uuid4())
            ids.append(entry_id)
            rows.append(
                {
                    "id": entry_id,
                    "field_name": item.get("field_name", ""),
                    "field_value": item.get("field_value", ""),
                    "snippet": item.get("snippet", ""),
                    "source_job_id": item.get("source_job_id", ""),
                    "source_filename": item.get("source_filename", ""),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "vector": vector.tolist(),
                }
            )

        await asyncio.to_thread(self._table.add, rows)
        return ids

    def list_entries(
        self,
        field_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        table = self._table.to_arrow()
        data = table.to_pydict()
        total = len(data.get("id", []))
        filtered_items: list[dict[str, str]] = []
        keyword = (field_name or "").strip()
        for idx in range(total):
            row = {
                "id": data["id"][idx],
                "field_name": data["field_name"][idx],
                "field_value": data["field_value"][idx],
                "snippet": data["snippet"][idx],
                "source_job_id": data["source_job_id"][idx],
                "source_filename": data["source_filename"][idx],
                "created_at": data["created_at"][idx],
            }
            if keyword and keyword not in row["field_name"]:
                continue
            filtered_items.append(row)

        effective_page = page if page >= 1 else 1
        effective_page_size = page_size if page_size >= 1 else 20
        start = (effective_page - 1) * effective_page_size
        end = start + effective_page_size
        return {"items": filtered_items[start:end], "total": len(filtered_items)}

    def delete_entry(self, entry_id: str) -> None:
        self._table.delete(f"id = '{entry_id}'")


_kb: KbService | None = None


def init_kb_service() -> None:
    global _kb
    import lancedb

    kb_dir = str(data_dir() / "kb")
    db = lancedb.connect(kb_dir)
    try:
        table = db.open_table(KB_TABLE_NAME)
    except Exception:
        table = db.create_table(KB_TABLE_NAME, schema=_KB_SCHEMA)

    svc = KbService(table)
    models_dir_raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
    if models_dir_raw:
        try:
            from sentence_transformers import SentenceTransformer

            model_path = Path(models_dir_raw) / "bge-m3"
            model = SentenceTransformer(str(model_path), local_files_only=True)
            model.encode(["预热"], show_progress_bar=False)
            svc.set_model(model)
        except Exception as exc:
            logger.warning("Failed to load local bge-m3 model, fallback to unavailable mode: %s", exc)
    _kb = svc


def get_kb_service() -> KbService | None:
    return _kb
