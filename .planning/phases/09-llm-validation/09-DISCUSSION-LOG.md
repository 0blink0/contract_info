# Phase 9 讨论日志

**日期：** 2026-05-26

## 选定灰区

全部（推荐默认快速过一遍）

## 讨论记录

| 主题 | 决定 |
|------|------|
| 触发时机 | extract 成功后自动校验（export 前） |
| 存储 | 新列 `validation_result` JSONB，与 extraction_warnings 分离 |
| 校验范围 | product_elements + 有摘录的 fee/subscription/path_b |
| 证据 | snippet 优先；不足时用 parse_json block_id |
| fail 行为 | 顾问式，不阻止 export |
| 本阶段 UI | 仅后端 API + JobDetail 摘要；前端 → Phase 10 |

## 延后

- VAL-04 完整前端高亮 → Phase 10
