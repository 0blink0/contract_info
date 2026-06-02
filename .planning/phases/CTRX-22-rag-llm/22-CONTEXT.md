# Phase 22: RAG 检索与 LLM 注入 - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段交付“业绩报酬提取前的语义检索注入”与“Top-K 配置项接入”：

1. 在业绩报酬提取链路触发向量检索（Top-K），检索历史知识库案例。
2. 将检索结果以 few-shot 结构注入 LLM prompt（字段名/字段值/原文摘录）。
3. 当知识库为空时自动降级为“不注入”，提取流程不报错。
4. Settings 增加 `RAG Top-K` 配置（默认 3，范围 1–10），并按既有设置流程生效。

不在本阶段：
- 扩展到 PathB 其它字段全面 RAG 注入
- 打包模型权重与 PyInstaller 离线兼容（Phase 23）
- 知识库检索可视化或高级检索策略（阈值、重排、多路召回）

</domain>

<decisions>
## Implementation Decisions

### 检索触发范围
- **D-01:** RAG 仅在“业绩报酬提取链路”触发，不扩展到 PathB 全链路其它字段。
- **D-02:** 检索输入优先使用业绩报酬相关原文上下文，不在本阶段引入额外多字段拼接策略。

### Prompt 注入结构
- **D-03:** 采用“按相似度排序的紧凑案例列表”注入 prompt，案例结构固定为：字段名 / 字段值 / 原文摘录。
- **D-04:** 不向模型显式注入相似度分数，仅保留排序结果，减少提示噪声。

### 空库降级
- **D-05:** 知识库为空（或无可用案例）时不注入 few-shot 块，直接走原始提取流程并保证无报错。
- **D-06:** 不注入“空案例占位提示”文本，避免对模型产生无效引导。

### Top-K 配置生效
- **D-07:** Settings 中 `RAG Top-K` 保存后按现有设置机制“重启后端生效”，不做热更新。
- **D-08:** 保持输入约束：整数、范围 1–10；非法值在设置层阻断并给出明确反馈。

### Claude's Discretion
- 检索 API 的内部函数拆分（service 层 vs extract 层）由 planner/researcher 结合现有代码组织决定。
- 注入模板在 `performance_fee.py` 与 `chapter_prompts.py` 的具体拼接位置由实现阶段确定，但须满足 D-03/D-04。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与阶段边界
- `contract_info/.planning/ROADMAP.md` — Phase 22 目标与 Success Criteria
- `contract_info/.planning/REQUIREMENTS.md` — `KB-RAG-01~04` 需求定义

### 已落地知识库能力（上游依赖）
- `contract_info/.planning/phases/CTRX-20-pathb-ui/20-CONTEXT.md` — 向量库、模型、软降级等既有决策
- `contract_info/backend/app/services/kb_service.py` — 知识库数据访问与检索扩展入口
- `contract_info/backend/app/api/routes/kb.py` — KB API 现有契约

### RAG 注入实现点
- `contract_info/backend/app/extract/llm/performance_fee.py` — 业绩报酬提取链路主注入点
- `contract_info/backend/app/extract/llm/chapter_prompts.py` — prompt 结构与拼接规则
- `contract_info/backend/app/extract/pipeline.py` — 抽取流程编排节点

### 配置与前端设置入口
- `contract_info/frontend/src/views/SettingsView.vue` — 设置页保存/重启生效模式
- `contract_info/frontend/src/components/LlmConfigForm.vue` — 表单约束与校验模式参考
- `contract_info/frontend/src/stores/appBootstrap.ts` — 设置生效与启动配置状态

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kb_service.py` 已具备知识库数据读写基础，可在该层扩展相似检索接口。
- `performance_fee.py` 已有 LLM 抽取调用与重试结构，适合插入 few-shot 构造步骤。
- `SettingsView.vue` 与 `LlmConfigForm.vue` 已有“保存并重启后端生效”标准交互。

### Established Patterns
- 后端抽取逻辑遵循 `extract/llm` 模块化分层，提示词和结构化解析分离。
- 前端设置项通过统一表单校验后提交，失败提示与回滚机制已固定。
- API 错误处理统一透传 `detail` 文案，前端展示中文可读提示。

### Integration Points
- 在业绩报酬提取前增加“检索 Top-K 案例”调用并产出注入块。
- 在 prompt 构造层追加“历史案例参考”片段，受 D-03/D-04 约束。
- 在 Settings 现有配置模型中新增 `RAG Top-K` 字段并纳入持久化/重启流程。

</code_context>

<specifics>
## Specific Ideas

- 注入块建议采用固定标题（如“历史案例参考”）+ 编号条目，保证模型输入稳定。
- Top-K 默认值沿用 3，避免初始提示过长；范围限制在 1–10 防止 prompt 膨胀。

</specifics>

<deferred>
## Deferred Ideas

- PathB 其它字段的 RAG 全面接入（本阶段仅业绩报酬链路）。
- 基于相似度阈值的动态过滤与重排策略。
- 将相似度分数暴露给模型或 UI 的能力。

</deferred>

---

*Phase: 22-RAG 检索与 LLM 注入*
*Context gathered: 2026-06-02*
