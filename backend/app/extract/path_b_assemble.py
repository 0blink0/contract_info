from __future__ import annotations

from typing import Any

from backend.app.extract.schemas import (
    FieldValue,
    OpenDayModule,
    PathBDocument,
    PerformanceFeeModule,
    PerformanceFeeTier,
)


def _fv_text(fv: FieldValue | None) -> str | None:
    if fv is None or fv.value is None:
        return None
    text = str(fv.value).strip()
    return text or None


def _fv_snippet(fv: FieldValue | None) -> str | None:
    if fv is None:
        return None
    snip = fv.snippet
    if snip is None or not str(snip).strip():
        return None
    return str(snip).strip()


def _add_snippet(snippets: dict[str, str], path: str, fv: FieldValue | None) -> None:
    snip = _fv_snippet(fv)
    if snip:
        snippets[path] = snip


def build_path_b_document(
    *,
    performance_fields: dict[str, FieldValue | None],
    open_day_fields: dict[str, FieldValue | None],
    tiers: list[PerformanceFeeTier],
) -> dict[str, Any]:
    perf = PerformanceFeeModule()
    if _fv_text(performance_fields.get("extraction_method")):
        perf.extraction_method = _fv_text(performance_fields.get("extraction_method"))
    if _fv_text(performance_fields.get("benchmark_type")):
        perf.benchmark_type = _fv_text(performance_fields.get("benchmark_type"))
    if _fv_text(performance_fields.get("hurdle_nav")):
        perf.hurdle_nav = _fv_text(performance_fields.get("hurdle_nav"))
    if _fv_text(performance_fields.get("extraction_timing")):
        perf.extraction_timing = _fv_text(performance_fields.get("extraction_timing"))
    if _fv_text(performance_fields.get("summary")):
        perf.summary = _fv_text(performance_fields.get("summary"))
    if _fv_text(performance_fields.get("manager_waiver")):
        perf.manager_waiver = _fv_text(performance_fields.get("manager_waiver"))
    perf.tiers = [t for t in tiers if t.description or t.ratio_pct or t.benchmark]

    open_day = OpenDayModule()
    if _fv_text(open_day_fields.get("fixed_schedule")):
        open_day.fixed_schedule = _fv_text(open_day_fields.get("fixed_schedule"))
    if _fv_text(open_day_fields.get("open_business")):
        open_day.open_business = _fv_text(open_day_fields.get("open_business"))
    if _fv_text(open_day_fields.get("temporary_open")):
        open_day.temporary_open = _fv_text(open_day_fields.get("temporary_open"))
    if _fv_text(open_day_fields.get("ad_hoc_rules")):
        open_day.ad_hoc_rules = _fv_text(open_day_fields.get("ad_hoc_rules"))

    snippets: dict[str, str] = {}
    for key, fv in performance_fields.items():
        if _fv_text(fv):
            _add_snippet(snippets, f"performance_fee.{key}", fv)
    for key, fv in open_day_fields.items():
        if _fv_text(fv):
            _add_snippet(snippets, f"open_day.{key}", fv)
    for idx, tier in enumerate(perf.tiers):
        prefix = f"performance_fee.tiers[{idx}]"
        if tier.description:
            snippets[f"{prefix}.description"] = tier.description
        if tier.ratio_pct:
            snippets.setdefault(f"{prefix}.ratio_pct", tier.description or tier.ratio_pct)

    doc = PathBDocument(
        performance_fee=perf,
        open_day=open_day,
        source_snippets=snippets,
    )
    return doc.model_dump(exclude_none=True)
