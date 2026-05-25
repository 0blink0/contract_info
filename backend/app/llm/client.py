from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


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
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json_object(content)
        return response_model.model_validate(parsed)
