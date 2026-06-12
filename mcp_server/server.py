#!/usr/bin/env python3
"""
Contract Info MCP Server

Wraps the contract_info parsing/extraction pipeline as MCP tools.
All data stored here is TEMPORARY — callers must call cleanup_job after saving
results to their own persistent storage.

Run: python server.py  (stdio transport, for use as a subprocess)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback
import uuid
from datetime import datetime
from pathlib import Path

# contract_info project root (…/contract_info/mcp_server/server.py → parents[1])
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv() -> None:
    """Load contract_info/.env into os.environ (httpx reads HTTP_PROXY from env)."""
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Temporary storage — one JSON file per job inside its own directory
# ---------------------------------------------------------------------------
_TEMP_BASE = Path(tempfile.gettempdir()) / "contract_mcp"
_TEMP_BASE.mkdir(exist_ok=True)

# Progress log — tail this file in a terminal to watch live progress
_LOG_PATH = _TEMP_BASE / "progress.log"


def _log(job_id: str, step: str, detail: str = "") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{job_id[:8]}] {step}"
    if detail:
        line += f" — {detail}"
    try:
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _job_meta_path(job_id: str) -> Path:
    return _TEMP_BASE / job_id / "meta.json"


def _read_job(job_id: str) -> dict | None:
    p = _job_meta_path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_job(job_id: str, data: dict) -> None:
    p = _job_meta_path(job_id)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# MCP server definition
# ---------------------------------------------------------------------------
mcp = FastMCP("contract-parser")


@mcp.tool()
def upload_contract(filename: str, file_path: str = "", file_content_base64: str = "") -> str:
    """
    Copy a DOCX contract file into temporary server storage.
    Must be called before process_contract.

    Provide either file_path (local server path) or file_content_base64 (base64-encoded
    file bytes, for remote/HTTP deployments where the file is on the client side).

    Args:
        filename:             Display name of the file (must end in .docx).
        file_path:            Absolute path to the .docx file on disk (local mode).
        file_content_base64:  Base64-encoded .docx file bytes (remote mode).

    Returns:
        JSON: {"job_id": str, "status": "uploaded"}
              or {"error": str} on failure.
    """
    import base64

    if not filename.lower().endswith(".docx"):
        return json.dumps({"error": "Only .docx files are supported"})

    job_id = str(uuid.uuid4())
    job_dir = _TEMP_BASE / job_id
    job_dir.mkdir()
    dest = job_dir / "input.docx"

    if file_content_base64:
        try:
            dest.write_bytes(base64.b64decode(file_content_base64))
        except Exception as e:
            shutil.rmtree(str(job_dir), ignore_errors=True)
            return json.dumps({"error": f"Failed to decode file content: {e}"})
    elif file_path:
        src = Path(file_path)
        if not src.exists():
            shutil.rmtree(str(job_dir), ignore_errors=True)
            return json.dumps({"error": f"File not found: {file_path}"})
        shutil.copy2(str(src), str(dest))
    else:
        shutil.rmtree(str(job_dir), ignore_errors=True)
        return json.dumps({"error": "Provide either file_path or file_content_base64"})

    _write_job(job_id, {
        "job_id": job_id,
        "filename": filename,
        "file_path": str(dest),
        "status": "uploaded",
        "created_at": datetime.now().isoformat(),
    })

    return json.dumps({"job_id": job_id, "filename": filename, "status": "uploaded"})


@mcp.tool()
async def process_contract(
    job_id: str,
    openai_api_key: str = "",
    openai_base_url: str = "",
    llm_model: str = "",
) -> str:
    """
    Parse and extract all structured information from an uploaded contract.
    Runs the full pipeline: DOCX → parse blocks → LLM extraction → Path-B build.

    Args:
        job_id:          Returned by upload_contract.
        openai_api_key:  Optional. Overrides OPENAI_API_KEY env var for this call.
        openai_base_url: Optional. Overrides OPENAI_BASE_URL env var.
        llm_model:       Optional. Overrides llm_model setting.

    Returns:
        JSON with keys:
          job_id, filename, parse_summary, extraction, path_b, warnings
        or {"error": str, "traceback": str, "job_id": str} on failure.
    """
    meta = _read_job(job_id)
    if not meta:
        return json.dumps({"error": f"Job not found: {job_id}"})

    filename = meta["filename"]
    file_path = meta["file_path"]

    # Override LLM settings via env vars so existing config.py picks them up
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if openai_base_url:
        os.environ["OPENAI_BASE_URL"] = openai_base_url
    if llm_model:
        os.environ["LLM_MODEL"] = llm_model

    try:
        _log(job_id, "STARTED", filename)

        # Clear lru_cache so fresh env vars take effect
        from backend.app.config import get_settings
        get_settings.cache_clear()

        # ── Phase 1: Parse DOCX ──────────────────────────────────────────
        _log(job_id, "STEP 1/3", "解析 DOCX 文档结构")
        from backend.app.parse.docx_parser import parse_docx
        parse_result = parse_docx(file_path)
        block_count = len(parse_result.get("blocks", []))
        _log(job_id, "STEP 1/3 OK", f"{block_count} 个文本块")

        parse_summary = {
            "metadata": parse_result.get("metadata", {}),
            "outline": parse_result.get("outline", [])[:20],
        }

        # ── Phase 2: Extract structured fields ──────────────────────────
        _log(job_id, "import:pipeline", "开始")
        from backend.app.extract.pipeline import extract_document
        from backend.app.llm.client import LlmClient
        _log(job_id, "import:pipeline", "完成")

        llm_client = LlmClient()
        _log(job_id, "LlmClient()", f"model={llm_client.model_name} available={llm_client.available}")

        _log(job_id, "STEP 2/3", "开始 extract_document")
        extraction_result, warnings, path_b = await extract_document(
            parse_result,
            llm_client=llm_client,
        )
        _log(job_id, "STEP 2/3 OK", f"提取完成，warnings={len(warnings)}")

        extraction_dict = extraction_result.model_dump(mode="json")
        warnings_list = [w.model_dump(mode="json") for w in warnings]

        # Update meta file with results
        _log(job_id, "STEP 3/3", "保存结果")
        meta.update({"status": "processed"})
        _write_job(job_id, meta)

        return json.dumps(
            {
                "job_id": job_id,
                "filename": filename,
                "parse_summary": parse_summary,
                "extraction": extraction_dict,
                "path_b": path_b,
                "warnings": warnings_list,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        _log(job_id, "ERROR", f"{type(exc).__name__}: {exc}")
        meta.update({"status": "failed"})
        _write_job(job_id, meta)
        return json.dumps(
            {
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "job_id": job_id,
            }
        )


@mcp.tool()
def cleanup_job(job_id: str) -> str:
    """
    Delete all temporary files for a job.
    Call this AFTER the agent has saved results to its own persistent database.

    Args:
        job_id: Job ID returned by upload_contract.

    Returns:
        JSON: {"status": "cleaned"|"not_found", "job_id": str}
    """
    job_dir = _TEMP_BASE / job_id
    if not job_dir.exists():
        return json.dumps({"status": "not_found", "job_id": job_id})

    shutil.rmtree(str(job_dir), ignore_errors=True)
    return json.dumps({"status": "cleaned", "job_id": job_id})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run in HTTP/SSE mode instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.http:
        from mcp.server.fastmcp import FastMCP as _FastMCP
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()
