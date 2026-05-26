# Phase 9：LLM 校验层 — 调研

**调研日期：** 2026-05-26  
**领域：** 摘录一致性 LLM 审查、validation_result 持久化、API  
**置信度：** HIGH（`LlmClient.chat_json` 已验证）/ MEDIUM（批处理 token 上限）

<user_constraints>
## 用户约束（09-CONTEXT.md）

- D-T01/T02：extract 后自动校验；无 Key 则 skipped + warning
- D-P01–03：validation_result JSONB 独立结构
- D-S01–03：product + fee/subscription/path_b 有证据字段
- D-E01–03：snippet 优先，block_id 补全；分批 prompt
- D-V01：advisory，不阻止 export
- D-A01–03：GET /validation + JobDetail 摘要；无前端
</user_constraints>

<phase_requirements>
| ID | 描述 | 调研结论 |
|----|------|----------|
| VAL-01 | 抽取后 LLM 校验 value vs snippet | `validation_service.run_validation` 在 `persist_extract` 末尾 |
| VAL-02 | 不用黄金 xlsx | prompt 禁止引用外部表；测试无 xlsx 读取 |
| VAL-03 | validation_result 结构 | Pydantic `ValidationResult` → JSONB |
| VAL-04 | 前端高亮 | **Phase 10**；本阶段仅 API |
| TEST-02 | 矛盾样例 fail | mock `chat_json` 返回 fail status |
</phase_requirements>

## 摘要

新建 **`backend/app/validate/`** 包（与 `extract/validate.py` 枚举校验区分），包含：候选字段收集、`llm_validator` 批审、`validation_service` 持久化。`extract/validate.py` **保持不动**（仅 dict 枚举）。

## 推荐 Schema

```python
class ValidationItem(BaseModel):
    field: str
    status: Literal["pass", "warn", "fail"]
    value: str | None = None
    reason: str
    suggestion: str | None = None

class ValidationResult(BaseModel):
    validated_at: str
    model: str | None = None
    skipped: bool = False
    items: list[ValidationItem] = Field(default_factory=list)
    summary: dict[str, int]  # pass, warn, fail
```

## 候选字段收集（evidence.py）

| 来源 | field 路径示例 | 证据 |
|------|----------------|------|
| product_elements | `管理人` | FieldValue.snippet / block_id |
| fee_rates[i] | `fee_rates[0].运营费类型` | 行内 snippet 若存在 |
| subscription_fees[i] | `subscription_fees[0].费率` | 同上 |
| path_b_json | `path_b.performance_fee.tiers[0].ratio_pct` | source_snippets 键 |

**跳过：** value 为空；无 snippet 且无 block_id。

## LLM 批处理

- 每批 **8–12** 个字段（可配置 `VALIDATION_BATCH_SIZE`）
- Response model：`ValidationBatchResponse` 含 `items: list[{field, status, reason, suggestion?}]`
- Prompt 规则：值须被摘录支持；当事人须为公司全称出现在摘录；矛盾 → fail

## 架构变更

| 文件 | 变更 |
|------|------|
| `validate/schemas.py` | ValidationItem/Result |
| `validate/evidence.py` | `collect_validation_candidates` |
| `validate/llm_validator.py` | `run_llm_validation` |
| `services/validation_service.py` | `persist_validation(file_id)` |
| `services/extract_service.py` | extract 后调用 validation |
| `models/contract_file.py` | `validation_result` |
| `alembic/007_validation_result.py` | 迁移 |
| `api/routes/jobs.py` | GET `/validation` |

## 测试

- `test_validation_evidence.py` — 候选收集数量
- `test_llm_validator.py` — mock client：一致→pass，矛盾→fail（TEST-02）
- `test_api_validation.py` — API 门禁
- 可选 `test_validation_llm.py` @pytest.mark.llm

## 风险

1. **包名冲突** — 使用 `backend.app.validate` 与 `extract.validate` 模块路径不同，import 时用全路径
2. **异步校验** — `persist_extract` 需 `asyncio.run(run_llm_validation)` 或 sync wrapper
3. **重复校验** — export-only 重跑 pipeline 时不重复校验（仅当 validation_result 为空或显式 revalidate）

---
*Phase 9 research — ready for planning*
