from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
FieldSource = Literal["rule", "llm", "manual", "fixed"]


class FieldValue(BaseModel):
    value: str | float | None = None
    confidence: Confidence = "medium"
    source: FieldSource = "rule"
    block_id: str | None = None
    section_id: str | None = None
    snippet: str | None = None


class LockPeriodRow(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    产品名称: str | None = None
    份额类型: str | None = None
    锁定期: str | None = None
    投资者类型: str | None = None
    客户名称: str | None = None
    客户证件类型: str | None = None
    客户证件号码: str | None = None
    锁定时间: str | None = None
    起始规则: str | None = None
    解锁方式: str | None = None
    解锁批次: str | None = None
    继承原交易锁定期: str | None = None
    生效时间: str | None = None


class ShareClassRow(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    基金全称: str | None = None
    基金代码: str | None = None
    分级份额名称: str | None = None
    分级份额简称: str | None = None
    分级份额代码: str | None = None
    代码类型: str | None = None
    分级类型: str | None = None
    实际成立日期: str | None = None
    投资起始日: str | None = None
    预警线: str | None = None
    止损线: str | None = None


class PerformanceFeeTier(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    share_class: str | None = None
    benchmark: str | None = None
    threshold: str | None = None
    ratio_pct: str | None = None
    description: str | None = None


class PerformanceFeeModule(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    extraction_method: str | None = None
    benchmark_type: str | None = None
    hurdle_nav: str | None = None
    extraction_timing: str | None = None
    summary: str | None = None
    manager_waiver: str | None = None
    tiers: list[PerformanceFeeTier] = Field(default_factory=list)


class OpenDayModule(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    fixed_schedule: str | None = None
    open_business: str | None = None
    temporary_open: str | None = None
    ad_hoc_rules: str | None = None


class PathBDocument(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    performance_fee: PerformanceFeeModule = Field(default_factory=PerformanceFeeModule)
    open_day: OpenDayModule = Field(default_factory=OpenDayModule)
    source_snippets: dict[str, str] = Field(default_factory=dict)
    raw_sections: dict[str, str] = Field(default_factory=dict)


class SubscriptionFeeRow(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    基金名称: str | None = None
    基金代码: str | None = None
    申赎费类型: str | None = None
    snippet: str | None = None
    计费方式: str | None = None
    费率生效日期: str | None = None
    计费基准: str | None = None
    时间区间单位: str | None = None
    区间开始: str | None = None
    区间结束: str | None = None
    费率类型: str | None = None
    费率: str | None = None


class FeeRateRow(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    基金名称: str | None = None
    基金代码: str | None = None
    运营费类型: str | None = None
    计费起始日期: str | None = None
    计费截止日期: str | None = None
    计费频率: str | None = None
    计费基准: str | None = None
    固定金额: str | None = None
    年计提天数: str | None = None
    费用计算方式: str | None = None
    支付频率: str | None = None
    费率生效日期: str | None = None
    rate_annual_pct: str | None = Field(None, alias="费率（%/年）")
    保底: str | None = None
    封顶: str | None = None


class ExtractionMeta(BaseModel):
    model: str | None = None
    chapters_called: list[str] = Field(default_factory=list)
    truncated_windows: list[str] = Field(default_factory=list)
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ExtractionResult(BaseModel):
    product_elements: dict[str, FieldValue] = Field(default_factory=dict)
    fee_rates: list[FeeRateRow] = Field(default_factory=list)
    subscription_fees: list[SubscriptionFeeRow] = Field(default_factory=list)
    lock_periods: list[LockPeriodRow] = Field(default_factory=list)
    share_classes: list[ShareClassRow] = Field(default_factory=list)
    meta: ExtractionMeta = Field(default_factory=ExtractionMeta, alias="_meta")

    model_config = {"populate_by_name": True}


class ExtractionWarning(BaseModel):
    field: str
    code: str
    message: str
    suggestion: str | None = None


def extraction_result_to_dict(result: ExtractionResult) -> dict[str, Any]:
    data = result.model_dump(by_alias=True, exclude_none=False)
    elements: dict[str, Any] = {}
    for key, fv in data.get("product_elements", {}).items():
        if isinstance(fv, dict):
            elements[key] = fv
        else:
            elements[key] = fv
    data["product_elements"] = elements
    data["fee_rates"] = [
        row if isinstance(row, dict) else row.model_dump(by_alias=True)
        for row in data.get("fee_rates", [])
    ]
    data["lock_periods"] = [
        row if isinstance(row, dict) else row.model_dump(by_alias=True)
        for row in data.get("lock_periods", [])
    ]
    data["share_classes"] = [
        row if isinstance(row, dict) else row.model_dump(by_alias=True)
        for row in data.get("share_classes", [])
    ]
    data["subscription_fees"] = [
        row if isinstance(row, dict) else row.model_dump(by_alias=True)
        for row in data.get("subscription_fees", [])
    ]
    return data


def warnings_to_list(warnings: list[ExtractionWarning]) -> list[dict[str, Any]]:
    return [w.model_dump(exclude_none=True) for w in warnings]
