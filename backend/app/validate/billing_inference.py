"""Infer 价内/价外 from contract formulas — used by deterministic validation only."""

from __future__ import annotations

import re


def _infer_subscribe_or_purchase_billing(text: str, kind: str) -> str | None:
    if not text.strip():
        return None
    _eq = r"[=＝]"
    amount, fee, rate = f"{kind}金额", f"{kind}费用", f"{kind}费率"
    net, share = f"净{kind}金额", f"{kind}份额"

    if re.search(
        rf"{net}\s*{_eq}\s*{amount}\s*[×x＊]?\s*[（(]?\s*1\s*[-－]\s*{rate}",
        text,
    ):
        return "价内法"
    if re.search(
        rf"{fee}\s*{_eq}\s*{amount}\s*[×x＊]?\s*{rate}\s*/\s*[（(]?\s*1\s*\+",
        text,
    ):
        return "价外法"
    if re.search(rf"{fee}\s*{_eq}\s*{amount}\s*[×x＊]?\s*{rate}", text):
        return "价内法"
    if re.search(
        rf"{net}\s*{_eq}\s*{amount}\s*/\s*[（(]?\s*1\s*\+\s*{rate}",
        text,
    ):
        return "价外法"
    if re.search(
        rf"{share}\s*{_eq}\s*[（(]?\s*{amount}\s*[-－]\s*{fee}",
        text,
    ):
        return "价外法"
    if kind == "申购" and re.search(
        rf"{share}\s*{_eq}\s*{amount}\s*/\s*[（(]?\s*1\s*\+\s*{rate}",
        text,
    ):
        return "价外法"
    if kind == "申购" and re.search(
        r"申购金额\s*/\s*[（(]?\s*1\s*\+\s*申购费率\s*[）)]?\s*/\s*申购价格",
        text,
    ):
        return "价外法"
    if kind == "认购" and re.search(
        r"认购金额\s*/\s*[（(]?\s*1\s*\+\s*认购费率",
        text,
    ):
        return "价外法"
    return None


def infer_subscription_billing_rules(text: str) -> dict[str, str]:
    if not text.strip():
        return {}
    out: dict[str, str] = {}
    sub_scope = "\n".join(
        line for line in text.splitlines() if "认购" in line or "募集" in line
    )
    pur_scope = "\n".join(line for line in text.splitlines() if "申购" in line)
    sub_b = _infer_subscribe_or_purchase_billing(sub_scope or text, "认购")
    if sub_b:
        out["认购费"] = sub_b
    pur_b = _infer_subscribe_or_purchase_billing(pur_scope or text, "申购")
    if pur_b:
        out["申购费"] = pur_b

    _eq = r"[=＝]"
    if re.search(
        rf"赎回金额\s*{_eq}[^。\n]{{0,160}}?赎回费用",
        text,
    ) or re.search(
        rf"赎回费用\s*{_eq}\s*赎回(?:份数|份额)\s*[×x＊]\s*赎回价格\s*[×x＊]\s*赎回费率",
        text,
    ):
        out["赎回费"] = "价内法"
    elif re.search(
        rf"赎回份额\s*{_eq}\s*赎回金额\s*/\s*（?\s*1\s*\+\s*赎回费率",
        text,
    ):
        out["赎回费"] = "价外法"

    if re.search(r"价内法|价内收费|内扣|前端收费", text):
        if "认购" in text and "认购费" not in out:
            out.setdefault("认购费", "价内法")
        if "申购" in text and "申购费" not in out:
            out.setdefault("申购费", "价内法")
    if re.search(r"价外法|价外收费|外扣", text):
        if "认购" in text and "认购费" not in out:
            out.setdefault("认购费", "价外法")
        if "申购" in text and "申购费" not in out:
            out.setdefault("申购费", "价外法")
    return out
