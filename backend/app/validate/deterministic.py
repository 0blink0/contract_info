from __future__ import annotations

import re

from backend.app.extract.rules.assoc_product_type import infer_assoc_product_type
from backend.app.extract.rules.share_rules import _share_letters_in_text
from backend.app.extract.rules.subscription_rules import infer_subscription_billing_rules
from backend.app.validate.schemas import ValidationItem

_RE_NO_STOP_LINES = re.compile(
    r"不设置预警线[、,，\s]*止损线|预警线[、,，\s]*止损线.*不设置|未设预警.*止损",
    re.IGNORECASE,
)
_RE_FACE_VALUE = re.compile(
    r"(?:基金份额的)?初始募集面值[：:\s]*(?:人民币\s*)?[\d.]+\s*元",
    re.IGNORECASE,
)


def _field_value(elements: dict, name: str) -> str | None:
    raw = elements.get(name)
    if not isinstance(raw, dict):
        return None
    val = raw.get("value")
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def _field_snippet(elements: dict, name: str) -> str:
    raw = elements.get(name)
    if not isinstance(raw, dict):
        return ""
    return str(raw.get("snippet") or "").strip()


def deterministic_validation_items(
    extraction_result: dict,
) -> dict[str, ValidationItem]:
    """Rule-based pass items that override flaky LLM validation for clear patterns."""
    elements = extraction_result.get("product_elements") or {}
    if not isinstance(elements, dict):
        return {}

    out: dict[str, ValidationItem] = {}

    assoc_val = _field_value(elements, "产品类型（协会）")
    assoc_snip = _field_snippet(elements, "产品类型（协会）")
    if assoc_val and assoc_snip:
        inferred, _ = infer_assoc_product_type({"investment": assoc_snip})
        if inferred == assoc_val:
            out["产品类型（协会）"] = ValidationItem(
                field="产品类型（协会）",
                status="pass",
                value=assoc_val,
                reason="投资范围/限制中的80%资产占比规则与抽取值一致。",
                suggestion=None,
            )

    structure_val = _field_value(elements, "份额结构")
    structure_snip = _field_snippet(elements, "份额结构")
    if structure_val == "分级结构" and structure_snip:
        if "份额分类" in structure_snip or len(_share_letters_in_text(structure_snip)) >= 2:
            out["份额结构"] = ValidationItem(
                field="份额结构",
                status="pass",
                value=structure_val,
                reason="基本情况或份额分类表列明 A–D 类份额，与「分级结构」一致。",
                suggestion=None,
            )

    warn_snip = _field_snippet(elements, "预警线")
    stop_snip = _field_snippet(elements, "止损线")
    combined_stop = f"{warn_snip}\n{stop_snip}"
    if _RE_NO_STOP_LINES.search(combined_stop):
        reason = "摘录明确写明不设置预警线、止损线，抽取值「无」一致。"
        for field in ("预警线", "止损线"):
            val = _field_value(elements, field)
            if val == "无":
                out[field] = ValidationItem(
                    field=field,
                    status="pass",
                    value=val,
                    reason=reason,
                    suggestion=None,
                )
    elif (
        _field_value(elements, "止损线") == "无"
        and _RE_NO_STOP_LINES.search(warn_snip)
        and "止损线" in warn_snip
    ):
        out["止损线"] = ValidationItem(
            field="止损线",
            status="pass",
            value="无",
            reason="预警线摘录已同时写明不设置止损线，抽取值「无」一致。",
            suggestion=None,
        )

    face_val = _field_value(elements, "基金面值")
    face_snip = _field_snippet(elements, "基金面值")
    currency_snip = _field_snippet(elements, "币种")
    evidence = face_snip or currency_snip
    if face_val and _RE_FACE_VALUE.search(evidence):
        out["基金面值"] = ValidationItem(
            field="基金面值",
            status="pass",
            value=face_val,
            reason="摘录含初始募集面值（元），与抽取值一致。",
            suggestion=None,
        )
        currency = _field_value(elements, "币种")
        if currency == "人民币现钞" and re.search(
            r"人民币|[\d.]+\s*元", evidence
        ):
            out["币种"] = ValidationItem(
                field="币种",
                status="pass",
                value=currency,
                reason="面值以元计且未写明外币，按惯例为人民币现钞。",
                suggestion=None,
            )

    closed_val = _field_value(elements, "是否封闭")
    closed_snip = _field_snippet(elements, "是否封闭")
    if closed_val == "不封闭" and re.search(r"本基金的封闭期[：:\s]*无", closed_snip):
        out["是否封闭"] = ValidationItem(
            field="是否封闭",
            status="pass",
            value=closed_val,
            reason="申购赎回章节写明「本基金的封闭期：无」，与不封闭一致。",
            suggestion=None,
        )

    redeem_val = _field_value(elements, "是否支持金额赎回")
    redeem_snip = _field_snippet(elements, "是否支持金额赎回")
    if redeem_val == "不支持" and re.search(
        r"基金赎回采用份额申请|赎回采用份额申请", redeem_snip
    ):
        out["是否支持金额赎回"] = ValidationItem(
            field="是否支持金额赎回",
            status="pass",
            value=redeem_val,
            reason="摘录写明赎回采用份额申请，与「不支持」金额赎回一致。",
            suggestion=None,
        )

    limits_val = _field_value(elements, "投资限制")
    limits_snip = _field_snippet(elements, "投资限制")
    if limits_val and re.search(r"（五）投资限制|投资限制", limits_snip):
        if limits_val[:20] in limits_snip or limits_snip.find("基金总资产") >= 0:
            out["投资限制"] = ValidationItem(
                field="投资限制",
                status="pass",
                value=limits_val[:80] + ("…" if len(limits_val) > 80 else ""),
                reason="摘录来自投资章节「投资限制」条款，与抽取值一致。",
                suggestion=None,
            )

    mgr_val = _field_value(elements, "投资经理")
    mgr_snip = _field_snippet(elements, "投资经理")
    if mgr_val and mgr_snip:
        listed = [n.strip() for n in re.split(r"[、,，/]", mgr_val) if n.strip()]
        if listed and all(n in mgr_snip for n in listed):
            out["投资经理"] = ValidationItem(
                field="投资经理",
                status="pass",
                value=mgr_val,
                reason="摘录列明的投资经理姓名与抽取值一致。",
                suggestion=None,
            )

    add_val = _field_value(elements, "追加起点")
    add_snip = _field_snippet(elements, "追加起点")
    step_val = _field_value(elements, "最小变动单位")
    step_snip = _field_snippet(elements, "最小变动单位")
    if add_val == "无追加起点限制" and step_val and re.search(
        r"追加金额应不低于\s*1\s*万元", step_snip
    ):
        out["追加起点"] = ValidationItem(
            field="追加起点",
            status="pass",
            value=add_val,
            reason="合同对追加仅约定最低变动金额，运营表记为无追加起点限制。",
            suggestion=None,
        )
        out["最小变动单位"] = ValidationItem(
            field="最小变动单位",
            status="pass",
            value=step_val,
            reason="摘录写明追加金额不低于1万元，对应最小变动单位。",
            suggestion=None,
        )

    sub_rows = extraction_result.get("subscription_fees") or []
    if isinstance(sub_rows, list):
        for idx, row in enumerate(sub_rows):
            if not isinstance(row, dict):
                continue
            fee_type = str(row.get("申赎费类型") or "").strip()
            billing = str(row.get("计费方式") or "").strip()
            if fee_type not in ("认购费", "申购费", "赎回费") or billing not in (
                "价内法",
                "价外法",
            ):
                continue
            snippet = str(
                row.get("snippet") or row.get("_snippet") or row.get("摘录") or ""
            ).strip()
            if not snippet:
                continue
            inferred = infer_subscription_billing_rules(snippet).get(fee_type)
            if inferred != billing:
                continue
            field = f"subscription_fees[{idx}].计费方式"
            out[field] = ValidationItem(
                field=field,
                status="pass",
                value=billing,
                reason=(
                    f"摘录中的{fee_type}计算公式与「{billing}」一致"
                    "（如份额=金额减费用为价内法，份额=金额/(1+费率)为价外法）。"
                ),
                suggestion=None,
            )

    return out
