from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from backend.app.config import get_settings
from backend.app.extract.field_catalog import CRM_PERFORMANCE_FEE_FIELDS, DEFAULT_PRODUCT_VALUES, FIXED_PRODUCT_VALUES, SKIP_PRODUCT_FIELDS
from backend.app.extract.llm.fees_combined import extract_fees_combined_llm
from backend.app.extract.llm.perf_fee_section import extract_perf_fee_section_llm
from backend.app.extract.llm.product_combined import extract_product_combined_llm
from backend.app.extract.evidence_enrich import enrich_extraction_result
from backend.app.extract.path_b_llm import build_path_b_from_llm
from backend.app.extract.row_sort import sort_fee_rates, sort_subscription_fees
from backend.app.extract.schemas import (
    ExtractionMeta,
    ExtractionResult,
    ExtractionWarning,
    FieldValue,
    field_str,
)
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.subscription_billing import apply_subscription_billing
from backend.app.extract.text_sources import (
    gather_full_document_text,
    gather_subscription_rules_text,
)
from backend.app.extract.validate import validate_enums
from backend.app.llm.client import LlmClient
from backend.app.services.kb_service import get_kb_service

logger = logging.getLogger(__name__)



def _build_extraction_result(
    *,
    product_elements: dict[str, FieldValue],
    fee_rates: list,
    lock_periods: list,
    share_classes: list,
    subscription_fees: list,
    meta: ExtractionMeta,
) -> ExtractionResult:
    merged = dict(product_elements)
    for key in SKIP_PRODUCT_FIELDS:
        merged.pop(key, None)
    for fname, fval in FIXED_PRODUCT_VALUES.items():
        merged[fname] = FieldValue(value=fval, confidence="high", source="fixed")
    for fname, fval in DEFAULT_PRODUCT_VALUES.items():
        existing = merged.get(fname)
        if not existing or not (existing if isinstance(existing, str) else getattr(existing, "value", None)):
            merged[fname] = FieldValue(value=fval, confidence="low", source="rule")

    # 有 2 个及以上份额类别 → 份额结构强制为「分级」，覆盖 LLM 抽取值
    if len(share_classes) >= 2:
        merged["份额结构"] = FieldValue(value="分级", confidence="high", source="rule")

    warn = merged.get("预警线")
    stop = merged.get("止损线")
    if (
        warn
        and stop
        and str(warn.value).strip() == "无"
        and str(stop.value).strip() == "无"
        and warn.snippet
        and "止损线" in warn.snippet
        and (not stop.snippet or "止损线" not in stop.snippet)
    ):
        stop.snippet = warn.snippet

    return ExtractionResult(
        product_elements=merged,
        fee_rates=fee_rates,
        lock_periods=lock_periods,
        share_classes=share_classes,
        subscription_fees=subscription_fees,
        meta=meta,
    )


async def extract_document(
    document: dict[str, Any],
    *,
    llm_client: LlmClient | None = None,
) -> tuple[ExtractionResult, list[ExtractionWarning], dict[str, Any]]:
    windows, truncated = build_section_windows(document)
    warnings: list[ExtractionWarning] = []
    chapters_called: list[str] = []

    client = cast(Any, llm_client if llm_client is not None else LlmClient())
    if not getattr(client, "available", False):
        warnings.append(
            ExtractionWarning(
                field="llm",
                code="llm_unavailable",
                message="未配置 OPENAI_API_KEY，无法进行 LLM 抽取",
                suggestion="请在 .env 中配置 OPENAI_API_KEY 与 OPENAI_BASE_URL",
            )
        )
        meta = ExtractionMeta(model=None, chapters_called=[], truncated_windows=truncated)
        empty = _build_extraction_result(
            product_elements={},
            fee_rates=[],
            lock_periods=[],
            share_classes=[],
            subscription_fees=[],
            meta=meta,
        )
        return empty, warnings, {}

    full_text = gather_full_document_text(document)
    sub_fees_text = gather_subscription_rules_text(document, windows)

    # Product first so fees LLM can use 基金全称
    (
        llm_product_fields,
        lock_periods,
        share_classes,
        llm_open_day_raw,
        w_prod,
    ) = await extract_product_combined_llm(client, full_text, fund_name=None)
    warnings.extend(w_prod)

    fund_name = field_str(llm_product_fields, "基金全称")
    if llm_product_fields:
        chapters_called.append("product_combined")
    if lock_periods:
        chapters_called.append("lock")
    if share_classes:
        chapters_called.append("share")
    if llm_open_day_raw:
        chapters_called.append("open_day")

    rag_cases: list[dict[str, str]] = []
    fees_win = (windows.get("fees") or "").strip()
    if fees_win:
        kb_service = get_kb_service()
        if kb_service and not kb_service.model_available:
            logger.warning("KB RAG: model not ready, skipping RAG for this extraction")
            warnings.append(
                ExtractionWarning(
                    field="performance_fee.rag",
                    code="rag_model_loading",
                    message="KB 向量模型尚未就绪，本次提取跳过 RAG 注入",
                    suggestion="请检查 bge-m3 模型路径配置，模型加载完成后重新提交",
                )
            )
        if kb_service and kb_service.model_available:
            rag_top_k = min(max(int(get_settings().rag_top_k), 1), 10)
            try:
                field_results = await asyncio.gather(
                    *[
                        kb_service.search_similar_entries(fees_win, rag_top_k, field_name=f)
                        for f in CRM_PERFORMANCE_FEE_FIELDS
                    ]
                )
                rag_cases = [c for cases in field_results for c in cases]
                hit_fields = [f for f, cases in zip(CRM_PERFORMANCE_FEE_FIELDS, field_results) if cases]
                logger.info(
                    "KB RAG: field-level recall %d cases across fields: %s",
                    len(rag_cases),
                    hit_fields,
                )
                if rag_cases:
                    warnings.append(
                        ExtractionWarning(
                            field="performance_fee.rag",
                            code="rag_injected",
                            message=(
                                f"RAG 字段级召回 {len(rag_cases)} 条案例"
                                f"（命中字段：{'、'.join(hit_fields)}）"
                            ),
                            suggestion=None,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("KB RAG search failed: %s", exc)
                warnings.append(
                    ExtractionWarning(
                        field="performance_fee.rag",
                        code="kb_rag_search_failed",
                        message=str(exc),
                        suggestion="已自动降级为无案例注入",
                    )
                )

    # Collect known share class letters to help per-class fee extraction
    _share_labels: list[str] = []
    for _sc in share_classes:
        _lbl = (_sc.分级份额简称 or "").strip()
        if _lbl and _lbl not in _share_labels:
            _share_labels.append(_lbl)

    (fees_result, direct_perf_section) = await asyncio.gather(
        extract_fees_combined_llm(
            client,
            full_text,
            sub_fees_text,
            fund_name=fund_name,
            share_class_labels=_share_labels or None,
            rag_cases=rag_cases,
        ),
        extract_perf_fee_section_llm(client, full_text),
    )
    (
        llm_fee_rows,
        llm_sub_rows,
        llm_billing_map,
        llm_perf_raw,
        llm_perf_flag,
        crm_fields,
        chapter_fee_fields,
        fee_meta_snippet,
        crm_group_snippet,
        w_fees,
    ) = fees_result
    warnings.extend(w_fees)

    if llm_perf_raw:
        chapters_called.append("performance_fee")
    if llm_fee_rows:
        chapters_called.append("fee_rates_llm")
    if llm_sub_rows:
        chapters_called.append("subscription_fees_llm")
    if llm_fee_rows or llm_sub_rows or llm_perf_raw or crm_fields:
        chapters_called.append("fees_combined")

    kb_field_extractions: dict[str, tuple[str, str]] = {}
    for field, val in crm_fields.items():
        kb_field_extractions[field] = (val, crm_group_snippet or "")
    for field, val in chapter_fee_fields.items():
        llm_product_fields[field] = FieldValue(
            value=val,
            confidence="medium",
            source="llm",
            snippet=fee_meta_snippet,
        )

    apply_subscription_billing(llm_sub_rows, llm_billing_map)
    subscription_fees = sort_subscription_fees(llm_sub_rows)
    fee_rates = sort_fee_rates(llm_fee_rows)

    # Propagate global fee metadata to every FeeRateRow (including zero-fee rows).
    # The LLM returns 计费基准/年计提天数/费用计算方式 as top-level fields, not per-row;
    # all rows — regardless of rate — share the same calculation method for the fund.
    _META_FEE_FIELDS = ("计费基准", "年计提天数", "费用计算方式")
    for _field in _META_FEE_FIELDS:
        _val = chapter_fee_fields.get(_field, "").strip()
        if _val:
            for _row in fee_rates:
                if not (getattr(_row, _field, None) or "").strip():
                    setattr(_row, _field, _val)

    meta = ExtractionMeta(
        model=client.model_name,
        chapters_called=chapters_called,
        truncated_windows=truncated,
        lock_confirmed_empty=len(lock_periods) == 0 and bool(full_text.strip()),
        share_confirmed_empty=len(share_classes) == 0 and bool(full_text.strip()),
    )

    result = _build_extraction_result(
        product_elements=llm_product_fields,
        fee_rates=fee_rates,
        lock_periods=lock_periods,
        share_classes=share_classes,
        subscription_fees=subscription_fees,
        meta=meta,
    )

    warnings.extend(validate_enums(result))

    path_b_dict, path_b_warnings = build_path_b_from_llm(
        product_elements=result.product_elements,
        llm_perf_raw_section=llm_perf_raw,
        llm_perf_flag=llm_perf_flag,
        llm_open_day_raw_section=llm_open_day_raw,
        direct_perf_section=direct_perf_section or None,
        rag_cases=rag_cases,
        kb_field_extractions=kb_field_extractions,
    )
    warnings.extend(path_b_warnings)

    result = enrich_extraction_result(result, document)
    return result, warnings, path_b_dict


def extract_document_sync(
    document: dict[str, Any],
    *,
    llm_client: LlmClient | None = None,
) -> tuple[ExtractionResult, list[ExtractionWarning], dict[str, Any]]:
    return asyncio.run(extract_document(document, llm_client=llm_client))
