from __future__ import annotations



import asyncio

from typing import Any, cast



from backend.app.extract.field_catalog import LLM_WINDOW_KEYS

from backend.app.extract.llm.chapter_extract import extract_chapter_fields

from backend.app.extract.llm.subtable_extract import (

    extract_lock_periods_llm,

    extract_share_classes_llm,

)

from backend.app.extract.merge import merge_extraction, merge_field
from backend.app.extract.row_sort import sort_fee_rates, sort_subscription_fees

from backend.app.extract.rules import extract_fee_rates, extract_product_rules

from backend.app.extract.rules.fee_rules import enrich_fee_rates_from_product

from backend.app.extract.rules.lock_normalize import merge_lock_rows
from backend.app.extract.rules.lock_rules import extract_lock_periods_rules

from backend.app.extract.rules.share_merge import merge_share_classes
from backend.app.extract.rules.share_rules import (
    extract_share_classes_rules,
    is_graded_contract,
)
from backend.app.extract.rules.path_b_rules import extract_path_b_rules
from backend.app.extract.rules.subscription_rules import extract_subscription_fees_rules

from backend.app.extract.schemas import (

    ExtractionMeta,

    ExtractionResult,

    ExtractionWarning,

)

from backend.app.extract.section_windows import build_section_windows

from backend.app.extract.validate import validate_enums

from backend.app.llm.client import LlmClient





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





async def extract_document(

    document: dict[str, Any],

    *,

    llm_client: LlmClient | None = None,

) -> tuple[ExtractionResult, list[ExtractionWarning], dict[str, Any]]:

    windows, truncated = build_section_windows(document)

    product_rules = extract_product_rules(document, windows)



    fund_fv = product_rules.get("基金全称")

    fund_name = str(fund_fv.value) if fund_fv and fund_fv.value else None

    fee_rates = extract_fee_rates(windows.get("fees", ""), fund_name, document)



    llm_fields: dict[str, Any] = {}

    warnings: list[ExtractionWarning] = []

    chapters_called: list[str] = []



    client = cast(Any, llm_client if llm_client is not None else LlmClient())

    if getattr(client, "available", False):

        for key in LLM_WINDOW_KEYS:

            text = windows.get(key, "")

            if not text.strip():

                continue

            fields, w = await extract_chapter_fields(client, key, text)

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

    fee_rates = sort_fee_rates(enrich_fee_rates_from_product(fee_rates, merged_product))



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

    result = merge_extraction(

        product_rules,

        llm_fields,

        fee_rates,

        meta=meta,

        lock_periods=lock_periods,

        share_classes=share_classes,

        subscription_fees=subscription_fees,

    )

    warnings.extend(validate_enums(result))

    path_b_dict, path_b_warnings = extract_path_b_rules(
        document,
        windows,
        fund_name=fund_name,
        product_elements=merged_product,
    )
    warnings.extend(path_b_warnings)

    return result, warnings, path_b_dict





def extract_document_sync(

    document: dict[str, Any],

    *,

    llm_client: LlmClient | None = None,

) -> tuple[ExtractionResult, list[ExtractionWarning], dict[str, Any]]:

    return asyncio.run(extract_document(document, llm_client=llm_client))


