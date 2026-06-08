"""Assemble Path B document from LLM extraction outputs only."""

from __future__ import annotations

from typing import Any

from backend.app.extract.path_b_assemble import build_path_b_document
from backend.app.extract.schemas import ExtractionWarning, FieldValue


def _field_text(product_elements: dict[str, Any], key: str) -> str | None:
    fv = product_elements.get(key)
    if fv is None:
        return None
    val = fv.get("value") if isinstance(fv, dict) else getattr(fv, "value", None)
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def _fv(value: str, *, snippet: str = "") -> FieldValue:
    return FieldValue(
        value=value,
        confidence="medium",  # type: ignore[arg-type]
        source="llm",
        snippet=snippet or None,
    )


def build_path_b_from_llm(
    *,
    product_elements: dict[str, Any],
    llm_perf_raw_section: str | None,
    llm_perf_flag: str | None,
    llm_open_day_raw_section: str | None,
    rag_cases: list[dict[str, str]] | None = None,
    kb_field_extractions: dict[str, tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], list[ExtractionWarning]]:
    warnings: list[ExtractionWarning] = []
    perf_fields: dict[str, FieldValue | None] = {}
    open_fields: dict[str, FieldValue | None] = {}

    perf_raw = (llm_perf_raw_section or "").strip()
    perf_flag = (llm_perf_flag or "").strip()

    if perf_flag == "否":
        perf_fields["has_performance_fee"] = _fv("否", snippet=perf_raw)
        if perf_raw:
            perf_fields["summary"] = _fv(perf_raw, snippet=perf_raw)
    elif perf_flag in ("是", "条件性不计提"):
        perf_fields["has_performance_fee"] = _fv(perf_flag, snippet=perf_raw)
        if perf_raw:
            perf_fields["summary"] = _fv(perf_raw, snippet=perf_raw)
    elif perf_raw:
        perf_fields["has_performance_fee"] = _fv("是", snippet=perf_raw)
        perf_fields["summary"] = _fv(perf_raw, snippet=perf_raw)
    else:
        warnings.append(
            ExtractionWarning(
                field="path_b.performance_fee",
                code="path_b_incomplete",
                message="LLM 未返回业绩报酬原文",
                suggestion="请人工查阅费用与税收章节",
            )
        )

    open_rule = _field_text(product_elements, "开放日规则")
    if open_rule:
        open_fields["fixed_schedule"] = _fv(open_rule, snippet=open_rule)
    elif llm_open_day_raw_section:
        open_fields["fixed_schedule"] = _fv(
            llm_open_day_raw_section[:500],
            snippet=llm_open_day_raw_section,
        )
    else:
        warnings.append(
            ExtractionWarning(
                field="path_b.open_day.fixed_schedule",
                code="path_b_incomplete",
                message="LLM 未返回开放日规则或原文",
            )
        )

    raw_sections: dict[str, str] = {}
    if perf_raw:
        raw_sections["performance_fee"] = perf_raw
    if llm_open_day_raw_section and llm_open_day_raw_section.strip():
        raw_sections["open_day"] = llm_open_day_raw_section.strip()

    path_b = build_path_b_document(
        performance_fields=perf_fields,
        open_day_fields=open_fields,
        tiers=[],
        raw_sections=raw_sections,
        rag_cases=rag_cases,
        kb_field_extractions=kb_field_extractions,
    )
    return path_b, warnings
