from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.extract.field_catalog import LOCK_PERIOD_FIELDS, SHARE_CLASS_FIELDS
from backend.app.extract.schemas import ExtractionWarning, LockPeriodRow, ShareClassRow
from backend.app.llm.client import LlmClient


class LockRowsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rows: list[LockPeriodRow] = Field(default_factory=list)


class ShareRowsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rows: list[ShareClassRow] = Field(default_factory=list)


def _build_subtable_messages(
    table_label: str,
    fields: tuple[str, ...],
    text: str,
    *,
    fund_name: str | None,
) -> list[dict[str, str]]:
    field_list = "、".join(fields)
    system = (
        f"你是私募基金合同{table_label}抽取助手。根据合同片段输出 JSON："
        '{{"rows":[{{...}},...]}}。rows 中每个对象键名为中文，值为字符串；'
        "无法确定的键留空。无相关条款时 rows 为空数组。禁止 markdown。"
    )
    user = (
        f"【基金全称】{fund_name or '（未知）'}\n"
        f"【字段】{field_list}\n\n"
        f"【合同片段】\n{text[:12000]}\n\n"
        "请仅输出 JSON。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def _extract_rows(
    client: LlmClient | None,
    *,
    window_key: str,
    table_label: str,
    fields: tuple[str, ...],
    text: str,
    fund_name: str | None,
    response_cls: type[BaseModel],
) -> tuple[list, list[ExtractionWarning]]:
    if not client or not client.available or not text.strip():
        return [], []

    messages = _build_subtable_messages(table_label, fields, text, fund_name=fund_name)
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, response_cls)
            rows = list(parsed.rows)  # type: ignore[attr-defined]
            if table_label == "份额锁定期":
                for row in rows:
                    if fund_name and not row.产品名称:
                        row.产品名称 = fund_name
            else:
                for row in rows:
                    if fund_name and not row.基金全称:
                        row.基金全称 = fund_name
            return [r for r in rows if _row_has_value(r)], []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return [], [
        ExtractionWarning(
            field=f"subtable:{window_key}",
            code="llm_subtable_failed",
            message=last_err or "unknown",
            suggestion="保留规则层子表结果",
        )
    ]


def _row_has_value(row: LockPeriodRow | ShareClassRow) -> bool:
    return any(
        v is not None and str(v).strip() != ""
        for v in row.model_dump().values()
    )


async def extract_lock_periods_llm(
    client: LlmClient | None,
    text: str,
    *,
    fund_name: str | None,
) -> tuple[list[LockPeriodRow], list[ExtractionWarning]]:
    rows, warnings = await _extract_rows(
        client,
        window_key="lock",
        table_label="份额锁定期",
        fields=LOCK_PERIOD_FIELDS,
        text=text,
        fund_name=fund_name,
        response_cls=LockRowsResponse,
    )
    return rows, warnings


async def extract_share_classes_llm(
    client: LlmClient | None,
    text: str,
    *,
    fund_name: str | None,
) -> tuple[list[ShareClassRow], list[ExtractionWarning]]:
    rows, warnings = await _extract_rows(
        client,
        window_key="share",
        table_label="分级份额",
        fields=SHARE_CLASS_FIELDS,
        text=text,
        fund_name=fund_name,
        response_cls=ShareRowsResponse,
    )
    return rows, warnings
