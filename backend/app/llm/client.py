from __future__ import annotations

import json
import logging
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# Always write to project root (backend/app/llm/client.py → parents[3])
_DEBUG_LOG = Path(__file__).resolve().parents[3] / "llm_debug.log"


def _debug_log_path() -> Path:
    return _DEBUG_LOG


def _dbg(tag: str, **kwargs: Any) -> None:
    try:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] [{tag}] "
        line += " | ".join(f"{k}={str(v)!r}" for k, v in kwargs.items())
        p = _debug_log_path()
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty LLM response")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        obj = json.loads(match.group(0))
        if isinstance(obj, dict):
            return obj
    raise ValueError("no JSON object in LLM response")


class LlmClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = (settings.openai_api_key or "").strip()
        self._base_url = (settings.openai_base_url or "").rstrip("/")
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout
        self._max_tokens = settings.llm_max_tokens

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._base_url)

    @property
    def model_name(self) -> str:
        return self._model

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        if not self.available:
            raise RuntimeError("LLM client not configured (missing API key)")

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": self._max_tokens,
        }

        input_chars = sum(len(m.get("content", "")) for m in messages)
        _dbg("REQUEST", model=self._model, max_tokens=self._max_tokens,
             input_chars=input_chars, caller=response_model.__name__)

        raw_text: str = ""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                http_status = resp.status_code
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    _dbg("HTTP_ERROR", status=http_status,
                         body=resp.text[:2000], caller=response_model.__name__)
                    raise
                data = resp.json()

            finish_reason = (
                data.get("choices", [{}])[0].get("finish_reason", "?")
                if data.get("choices") else "no_choices"
            )
            usage = data.get("usage") or {}
            raw_text = data["choices"][0]["message"]["content"]
            _dbg("RESPONSE", finish_reason=finish_reason,
                 prompt_tokens=usage.get("prompt_tokens"),
                 completion_tokens=usage.get("completion_tokens"),
                 response_chars=len(raw_text),
                 response_head=raw_text[:300],
                 caller=response_model.__name__)

            if finish_reason == "length":
                _dbg("TRUNCATED", msg="Response cut off — max_tokens too low",
                     response_tail=raw_text[-200:], caller=response_model.__name__)

            parsed = _extract_json_object(raw_text)
            return response_model.model_validate(parsed)

        except Exception as exc:
            _dbg("EXCEPTION", exc_type=type(exc).__name__, exc=str(exc),
                 raw_head=raw_text[:500] if raw_text else "(empty)",
                 tb=traceback.format_exc()[-800:],
                 caller=response_model.__name__)
            raise
