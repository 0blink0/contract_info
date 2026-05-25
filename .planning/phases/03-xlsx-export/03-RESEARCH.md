# Phase 3 Research: Excel 模板填充

**Researched:** 2026-05-25  
**Phase:** 03 — export_xlsx

## Summary

用 **openpyxl** 复制 `templates/` 母版 → 按表头映射写入 `extraction_result` → 保存到 `exports/{file_id}/`。保留全部 sheet；产品要素 1 行、费率多行；必填缺失仅 warnings。

## 母版结构（来自 template_analysis.txt）

| 文件 | 数据 sheet | 表头行 | 首行数据 |
|------|------------|--------|----------|
| `产品要素-2.xlsx` | `产品要素模板` | 第 2 行 | 第 3 行 |
| `产品运营费率导入模板-1.xlsx` | `产品运营费率导入模板` | 第 3 行（含【必填】后缀） | 第 4 行起 |

费率表头需 **归一化**：去掉 `【必填】`、首尾空格再匹配映射。

## 推荐实现

1. **`shutil.copy2`** 母版 → 目标路径（保留格式与多 sheet）。
2. **`load_workbook`** 打开副本，定位 sheet 与表头行，构建 `{列名: col_index}`。
3. **重复列**：表头扫描时记录同名列出现次数，逻辑字段映射到 `list[int]` 列号，写相同值。
4. **产品要素**：`product_elements` 中 `FieldValue.value` → 单元格；日期字段走 `normalize_date_slash()`。
5. **费率**：遍历 `fee_rates`，`FeeRateRow.model_dump(by_alias=True)` + `COLUMN_MAP_FEE`。
6. **校验**：必填列表（基金全称、管理人、费率行 费率（%/年）等）→ `ExtractionWarning` code `export_required_missing`，合并进 `extraction_warnings`。

## DB

Migration `003`: `product_xlsx_path`, `fee_xlsx_path` TEXT nullable.  
Status: `exporting` → `exported` | `export_failed`.

## 风险

| 风险 | 规避 |
|------|------|
| 表头文案变更 | pytest 对比母版第 2/3 行列名列表 |
| 大文件 git | templates ~2 个 xlsx，可接受 |
| 示例行残留 | 费率从第 4 行写，覆盖示例行 4+ 仅 N 行 |

## Validation Architecture

| 维度 | 策略 |
|------|------|
| 表头一致 | pytest 读 templates 表头 == 写入后表头 |
| 端到端 | fixture extraction JSON → export → openpyxl 读回单元格 |
| DB | export --file-id integration skip 无 Docker |

## References

- `03-CONTEXT.md` D-01–D-15
- `template_analysis.txt`, `FIELD_SPEC.md`
