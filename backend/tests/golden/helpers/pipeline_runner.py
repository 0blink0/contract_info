from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.export.pipeline import (
    FEE_OUTPUT,
    LOCK_OUTPUT,
    PRODUCT_OUTPUT,
    SHARE_OUTPUT,
    SUBSCRIPTION_OUTPUT,
    export_xlsx,
)
from backend.app.extract.llm.fees_combined import _FeesCombinedResponse
from backend.app.extract.llm.product_combined import _ProductCombinedResponse
from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.schemas import FeeRateRow, LockPeriodRow, SubscriptionFeeRow
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.tests.golden.conftest import load_contract_expected


@dataclass
class GoldenRunResult:
    extraction: dict[str, Any]
    product_path: Path
    fee_path: Path
    lock_path: Path
    share_path: Path
    subscription_path: Path
    warnings: list[Any]


class GoldenMockLlm:
    """Inject golden expected values as LLM responses for export E2E tests."""

    available = True
    model_name = "golden-mock"

    def __init__(self, expected: dict[str, Any]) -> None:
        self._expected = expected

    def _product_response(self) -> _ProductCombinedResponse:
        e = self._expected
        product_fields = {
            k: e[k]
            for k in (
                "基金全称",
                "管理人",
                "托管人",
                "外包机构",
                "投资顾问",
                "风险等级",
                "锁定期",
                "开放日规则",
                "预警线",
                "止损线",
            )
            if e.get(k)
        }
        lock_rows = [
            LockPeriodRow(
                产品名称=e.get("基金全称"),
                份额类型=lp.get("份额类型"),
                锁定时间=lp.get("锁定时间"),
                投资者类型=lp.get("投资者类型"),
            )
            for lp in e.get("lock_periods") or []
        ]
        from backend.app.extract.schemas import ShareClassRow

        sub_by_share = e.get("subscription_fees_by_share") or {}
        share_rows = [
            ShareClassRow(
                基金全称=e.get("基金全称"),
                分级份额简称=letter,
                分级份额名称=f"{e.get('基金全称', '')}{letter}类",
            )
            for letter in sorted(sub_by_share.keys())
        ]
        return _ProductCombinedResponse.model_validate(
            {
                **product_fields,
                "锁定期子表": lock_rows,
                "份额分级子表": share_rows,
                "开放日原文": e.get("开放日规则") or "",
            }
        )

    def _fees_response(self) -> _FeesCombinedResponse:
        e = self._expected
        fund = e.get("基金全称") or ""
        fee_rows = [
            FeeRateRow(
                基金名称=fund,
                运营费类型=fee_type,
                rate_annual_pct=info.get("rate_annual_pct"),
            )
            for fee_type, info in (e.get("fee_rates_by_type") or {}).items()
        ]
        sub_rows: list[SubscriptionFeeRow] = []
        for letter, fees in (e.get("subscription_fees_by_share") or {}).items():
            if "证券投资基金" in fund:
                sub_fund = f"{fund}{letter.upper()}"
            else:
                sub_fund = f"{fund}{letter.upper()}类"
            for fee_type, rate in fees.items():
                sub_rows.append(
                    SubscriptionFeeRow(
                        基金名称=sub_fund,
                        申赎费类型=fee_type,
                        费率=rate,
                        计费基准="不分段",
                    )
                )
        return _FeesCombinedResponse.model_validate(
            {
                "运营费率": fee_rows,
                "申赎费率": sub_rows,
                "认购费计费方式": "价外法",
                "申购费计费方式": "价外法",
                "是否计提业绩报酬": "是",
                "业绩报酬原文": "业绩报酬条款（golden mock）",
            }
        )

    async def chat_json(self, messages, schema):  # noqa: ANN001
        del messages
        name = getattr(schema, "__name__", "")
        if name == "_ProductCombinedResponse":
            return self._product_response()
        if name == "_FeesCombinedResponse":
            return self._fees_response()
        raise ValueError(f"unexpected schema {schema}")


def _golden_llm_for_docx(docx_path: Path) -> GoldenMockLlm | None:
    key = docx_path.name
    expected_all = load_contract_expected()
    if key not in expected_all:
        return None
    return GoldenMockLlm(expected_all[key])


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
    mock = _golden_llm_for_docx(docx_path)
    if mock is None:
        import pytest

        pytest.skip(f"No golden fixture for {docx_path.name}")

    result, warnings, _path_b = extract_document_sync(document, llm_client=mock)  # type: ignore[arg-type]
    extraction = result.model_dump(mode="json")
    fid = uuid.uuid4()
    product_rel, fee_rel, lock_rel, share_rel, sub_rel, export_warnings = export_xlsx(
        extraction, fid
    )
    base = exports_root / str(fid)
    return GoldenRunResult(
        extraction=extraction,
        product_path=base / PRODUCT_OUTPUT,
        fee_path=base / FEE_OUTPUT,
        lock_path=base / LOCK_OUTPUT,
        share_path=base / SHARE_OUTPUT,
        subscription_path=base / SUBSCRIPTION_OUTPUT,
        warnings=list(warnings) + list(export_warnings),
    )
