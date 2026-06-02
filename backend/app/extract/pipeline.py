from __future__ import annotations



import asyncio
import logging

from typing import Any, cast



from backend.app.config import get_settings
from backend.app.extract.field_catalog import FIXED_PRODUCT_VALUES, LLM_WINDOW_KEYS
from backend.app.extract.schemas import FieldValue

from backend.app.extract.llm.chapter_extract import extract_chapter_fields

from backend.app.extract.llm.subtable_extract import (

    extract_lock_periods_llm,

    extract_share_classes_llm,

)

from backend.app.extract.evidence_enrich import enrich_extraction_result
from backend.app.extract.merge import merge_extraction, merge_field
from backend.app.extract.row_sort import sort_fee_rates, sort_subscription_fees

from backend.app.extract.rules import extract_fee_rates, extract_product_rules

from backend.app.extract.rules.fee_rules import (
    enrich_fee_rates_from_fees_chapter,
    enrich_fee_rates_from_product,
    gather_fee_source_text,
)

from backend.app.extract.rules.lock_normalize import merge_lock_rows
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules

from backend.app.extract.rules.classification_rules import (
    extract_classification_rules,
    infer_share_structure,
)
from backend.app.extract.rules.share_merge import merge_share_classes
from backend.app.extract.rules.share_rules import (
    extract_share_classes_rules,
    is_graded_contract,
)
from backend.app.extract.rules.path_b_rules import extract_path_b_rules
from backend.app.extract.llm.performance_fee import extract_performance_fee_section_llm
from backend.app.extract.llm.open_day import extract_open_day_section_llm
from backend.app.extract.llm.subscription_billing import extract_subscription_billing_llm
from backend.app.extract.rules.subscription_rules import (
    apply_subscription_billing,
    extract_subscription_fees_rules,
    gather_subscription_rules_text,
    infer_subscription_billing_rules,
)

from backend.app.extract.schemas import (

    ExtractionMeta,

    ExtractionResult,

    ExtractionWarning,

)

from backend.app.extract.section_windows import build_section_windows

from backend.app.extract.validate import validate_enums

from backend.app.llm.client import LlmClient
from backend.app.services.kb_service import get_kb_service
logger = logging.getLogger(__name__)


def _field_value(product: dict[str, Any], key: str) -> str | None:

    fv = product.get(key)

    if fv is None:

        return None

    if isinstance(fv, dict):

        val = fv.get("value")

    else:

        val = getattr(fv, "value", None)

    if val is None or str(val).strip() == "":

        return None

    return str(val).strip()


def _build_fees_rag_query(fees_window_text: str) -> str:
    # D-02: query 仅来源于业绩报酬相关上下文（fees window）。
    text = (fees_window_text or "").strip()
    if not text:
        return ""
    return f"业绩报酬相关上下文：\n{text}"





async def extract_document(

    document: dict[str, Any],

    *,

    llm_client: LlmClient | None = None,

) -> tuple[ExtractionResult, list[ExtractionWarning], dict[str, Any]]:

    windows, truncated = build_section_windows(document)

    product_rules = extract_product_rules(document, windows)



    fund_fv = product_rules.get("基金全称")

    fund_name = str(fund_fv.value) if fund_fv and fund_fv.value else None

    fee_source = gather_fee_source_text(windows.get("fees", ""), document)
    fee_rates = extract_fee_rates(fee_source, fund_name, document)



    llm_fields: dict[str, Any] = {}

    warnings: list[ExtractionWarning] = []

    chapters_called: list[str] = []



    client = cast(Any, llm_client if llm_client is not None else LlmClient())

    if getattr(client, "available", False):

        active_keys = [k for k in LLM_WINDOW_KEYS if (windows.get(k) or "").strip()]

        results = await asyncio.gather(
            *[extract_chapter_fields(client, k, windows[k]) for k in active_keys],
            return_exceptions=False,
        )

        for key, (fields, w) in zip(active_keys, results):

            llm_fields.update(fields)

            warnings.extend(w)

            if fields:

                chapters_called.append(key)



    meta = ExtractionMeta(

        model=client.model_name if client.available else None,

        chapters_called=chapters_called,

        truncated_windows=truncated,

    )

    merged_product: dict[str, Any] = dict(product_rules)

    for key, llm_fv in llm_fields.items():

        merged_product[key] = (
            merge_field(merged_product.get(key), llm_fv, field_name=key) or llm_fv
        )

    fee_rates = sort_fee_rates(
        enrich_fee_rates_from_product(
            enrich_fee_rates_from_fees_chapter(fee_rates, fee_source),
            merged_product,
        )
    )



    fund_code = _field_value(merged_product, "基金代码")

    lock_periods = list(

        extract_lock_periods_rules(

            fund_name,

            merged_product.get("锁定期"),

            windows.get("subscription", ""),

        )

    )

    share_classes = list(

        extract_share_classes_rules(

            document,

            windows,

            fund_name=fund_name,

            fund_code=fund_code,

            product_elements=merged_product,

        )

    )

    sub_text = windows.get("subscription", "")



    if getattr(client, "available", False):

        if sub_text.strip():

            llm_lock, w_lock = await extract_lock_periods_llm(

                client, sub_text, fund_name=fund_name

            )

            warnings.extend(w_lock)

            if llm_lock:
                lock_periods = merge_lock_rows(
                    llm_lock,
                    lock_periods,
                    combined_text=sub_text,
                )
                chapters_called.append("lock")

        share_text = sub_text + "\n" + windows.get("basic", "")

        graded = is_graded_contract(merged_product, windows)

        if share_text.strip() and (share_classes or graded):

            llm_share, w_share = await extract_share_classes_llm(

                client, share_text, fund_name=fund_name

            )

            warnings.extend(w_share)

            if llm_share:
                share_classes = merge_share_classes(share_classes, llm_share)
                chapters_called.append("share")

    subscription_fees = sort_subscription_fees(
        extract_subscription_fees_rules(
            document,
            windows,
            fund_name=fund_name,
            share_classes=share_classes,
            product_elements=merged_product,
        )
    )
    bill_text = gather_subscription_rules_text(document, windows)
    billing_map = infer_subscription_billing_rules(bill_text)
    if getattr(client, "available", False):
        llm_billing, w_bill = await extract_subscription_billing_llm(client, bill_text)
        warnings.extend(w_bill)
        for key, val in llm_billing.items():
            if val:
                billing_map[key] = val
        if llm_billing:
            chapters_called.append("subscription_billing")
    apply_subscription_billing(subscription_fees, billing_map)

    result = merge_extraction(

        product_rules,

        llm_fields,

        fee_rates,

        meta=meta,

        lock_periods=lock_periods,

        share_classes=share_classes,

        subscription_fees=subscription_fees,

    )

    pe = result.product_elements
    for key, fv in extract_classification_rules(
        document, windows, {k: v for k, v in pe.items()}
    ).items():
        pe[key] = merge_field(pe.get(key), fv, field_name=key) or fv

    structure_fv = infer_share_structure(share_classes, windows)
    if structure_fv:
        pe["份额结构"] = (
            merge_field(pe.get("份额结构"), structure_fv, field_name="份额结构")
            or structure_fv
        )

    for fname, fval in FIXED_PRODUCT_VALUES.items():
        pe[fname] = FieldValue(value=fval, confidence="high", source="fixed")

    warnings.extend(validate_enums(result))

    llm_perf_raw: str | None = None
    llm_perf_flag: str | None = None
    llm_open_day_raw: str | None = None
    if getattr(client, "available", False):
        fees_win = (windows.get("fees") or "").strip()
        sub_win = (windows.get("subscription") or "").strip()
        tasks = []
        rag_cases: list[dict[str, str]] = []
        if fees_win:
            kb_service = get_kb_service()
            query_text = _build_fees_rag_query(windows["fees"])
            if kb_service and query_text:
                rag_top_k = min(max(int(get_settings().rag_top_k), 1), 10)
                try:
                    rag_cases = (
                        await kb_service.search_similar_entries(query_text, rag_top_k)
                    )[:rag_top_k]
                except Exception as exc:  # noqa: BLE001
                    logger.warning("KB RAG search failed, degrade to empty cases: %s", exc)
                    warnings.append(
                        ExtractionWarning(
                            field="performance_fee.rag",
                            code="kb_rag_search_failed",
                            message=str(exc),
                            suggestion="已自动降级为无案例注入，不影响提取主流程",
                        )
                    )
            tasks.append(
                extract_performance_fee_section_llm(
                    client,
                    windows["fees"],
                    rag_cases=rag_cases,
                )
            )
        if sub_win:
            tasks.append(extract_open_day_section_llm(client, windows["subscription"]))
        if tasks:
            results_raw = await asyncio.gather(*tasks)
            idx = 0
            if fees_win:
                llm_perf_raw, llm_perf_flag, w_perf = results_raw[idx]
                warnings.extend(w_perf)
                if llm_perf_raw:
                    chapters_called.append("performance_fee")
                idx += 1
            if sub_win:
                llm_open_day_raw, w_open = results_raw[idx]
                warnings.extend(w_open)
                if llm_open_day_raw:
                    chapters_called.append("open_day")

    path_b_dict, path_b_warnings = extract_path_b_rules(
        document,
        windows,
        fund_name=fund_name,
        product_elements=merged_product,
        llm_perf_raw_section=llm_perf_raw,
        llm_perf_flag=llm_perf_flag,
        llm_open_day_raw_section=llm_open_day_raw,
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


