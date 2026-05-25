CHAPTER_FIELDS: dict[str, list[str]] = {
    "basic": [
        "基金类型",
        "管理类型",
        "份额结构",
        "结构类型",
        "产品类型（协会）",
        "产品存续期",
    ],
    "establish": ["成立日期", "备案日期", "到期日期"],
    "subscription": [
        "首次申购起点",
        "追加起点",
        "交易确认规则",
        "是否支持金额赎回",
        "是否封闭",
        "锁定期",
    ],
    "investment": ["预警线", "止损线"],
    "fees": ["计费频率", "计费基准"],
}


def build_messages(window_key: str, text: str) -> list[dict[str, str]]:
    fields = CHAPTER_FIELDS.get(window_key, [])
    field_list = "、".join(fields) if fields else "（无额外字段）"
    system = (
        "你是私募基金合同要素抽取助手。仅根据给定合同片段输出一个 JSON 对象，"
        "键名为中文，值为字符串；无法确定则该键为空字符串。"
        "禁止输出解释、markdown 或多余键。"
    )
    user = (
        f"【章节窗口】{window_key}\n"
        f"【需抽取字段】{field_list}\n\n"
        f"【合同片段】\n{text[:10000]}\n\n"
        "请仅输出 JSON 对象。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
