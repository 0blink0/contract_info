# Phase 3: Excel 模板填充 - Discussion Log

> Audit trail only.

**Date:** 2026-05-25  
**Areas:** 母版策略, 列映射, 必填缺失, 输出与 DB, CLI

## 母版与写入

| Decision | Choice |
|----------|--------|
| 母版目录 | `templates/` 提交 git |
| 保留 sheet | 数据 + 说明 + 字典 |
| 产品要素行数 | 每合同 1 行（第 3 行） |
| 费率行数 | 每条 fee_rates 一行 |

## 列映射

| Decision | Choice |
|----------|--------|
| 填写列范围 | 仅 extraction 有的 P1 |
| 重复列 | 两列同值 |
| 日期格式 | yyyy/m/d |
| 费率表头 | 别名映射表 |

## 必填缺失

| Decision | Choice |
|----------|--------|
| 缺失行为 | 仍导出 + warnings |
| 报告 | DB extraction_warnings + CLI |
| 基金代码 | 留空 |

## 输出与 DB

| Decision | Choice |
|----------|--------|
| 目录 | `exports/{file_id}/` |
| DB | product_xlsx_path, fee_xlsx_path |
| status | exported / export_failed |

## CLI

| Decision | Choice |
|----------|--------|
| 命令 | 独立 export |
| 输入 | 优先 --file-id，可选 --from-json |
| templates | 提交 git |
