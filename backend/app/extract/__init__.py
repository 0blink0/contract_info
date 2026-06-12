from __future__ import annotations

__all__ = ["extract_document_sync"]


def __getattr__(name: str):
    if name == "extract_document_sync":
        from backend.app.extract.pipeline import extract_document_sync
        return extract_document_sync
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
