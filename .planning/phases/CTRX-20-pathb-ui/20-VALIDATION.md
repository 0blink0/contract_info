---
phase: 20
slug: pathb-kb-entry-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 20 — 验证策略

> 本阶段每任务提交后的反馈采样合同。

---

## 测试基础设施

| 属性 | 值 |
|------|----|
| **框架** | pytest 8.x（现有） |
| **配置文件** | `backend/tests/conftest.py` |
| **快速运行命令** | `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -x -q` |
| **完整套件命令** | `pytest backend/tests/ -x -q` |
| **前端类型检查** | `cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json` |
| **预计运行时间** | ~30 秒（不含 bge-m3 真实加载；使用 mock） |

---

## 采样频率

- **每任务提交后：** 运行 `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -x -q`
- **每波次合并后：** 运行 `pytest backend/tests/ -x -q`
- **`/gsd:verify-work` 前：** 完整套件必须为绿色 + 前端 `vue-tsc --noEmit` 通过
- **最大反馈延迟：** 30 秒

---

## 每任务验证映射

| 任务 | 波次 | 需求 | 测试类型 | 自动化命令 | 文件存在 | 状态 |
|------|------|------|----------|-----------|---------|------|
| kb_service init | Wave 0 | KB-BE-01 | unit | `pytest backend/tests/test_kb_service.py::test_init_creates_table -x` | ❌ Wave 0 | ⬜ pending |
| kb_service soft degrade | Wave 0 | KB-BE-02 | unit | `pytest backend/tests/test_kb_service.py::test_model_unavailable_soft_degrade -x` | ❌ Wave 0 | ⬜ pending |
| POST /kb/entries 成功 | Wave 0 | KB-BE-03 | integration | `pytest backend/tests/test_api_kb.py::test_post_entries_success -x` | ❌ Wave 0 | ⬜ pending |
| POST /kb/entries 503 | Wave 0 | KB-BE-03 | integration | `pytest backend/tests/test_api_kb.py::test_post_entries_503_when_no_model -x` | ❌ Wave 0 | ⬜ pending |
| GET /kb/entries 列表 | Wave 0 | KB-BE-04 | integration | `pytest backend/tests/test_api_kb.py::test_get_entries -x` | ❌ Wave 0 | ⬜ pending |
| GET /kb/entries?field_name 过滤 | Wave 0 | KB-BE-04 | integration | `pytest backend/tests/test_api_kb.py::test_get_entries_filter -x` | ❌ Wave 0 | ⬜ pending |
| DELETE /kb/entries/{id} | Wave 0 | KB-BE-05 | integration | `pytest backend/tests/test_api_kb.py::test_delete_entry -x` | ❌ Wave 0 | ⬜ pending |
| KB 录入区渲染（前端） | Wave 2 | KB-ENTRY-01~05 | 手动 | — | N/A | ⬜ pending |

*状态：⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 依赖

Wave 0 必须在 Wave 1 前完成（新增测试文件 + 依赖安装）：

- [ ] `backend/tests/test_kb_service.py` — KB-BE-01、KB-BE-02 unit 测试（mock model，`tmp_path` 提供临时 LanceDB 目录）
- [ ] `backend/tests/test_api_kb.py` — KB-BE-03~05 TestClient integration 测试（patch `KbService._model` 返回 mock，`encode` 返回 `np.zeros((n, 1024), dtype=np.float32)`）
- [ ] `requirements.txt` — 新增 `lancedb>=0.33.0` 和 `sentence-transformers>=5.5.1`

**Wave 0 验证：** `pytest backend/tests/test_kb_service.py backend/tests/test_api_kb.py -x -q`（需全绿）

---

## 仅手动验证项

| 行为 | 需求 | 手动原因 | 测试步骤 |
|------|------|---------|---------|
| PathB 页底部 KB 录入表格渲染（3 列 4 行） | KB-ENTRY-01 | 无前端自动化框架（无 Vitest/Playwright） | 进入一个有 PathB 数据的任务 → 滚动到底部 → 确认表格可见且有 4 行 |
| 字段值 / 原文摘录单元格可编辑 | KB-ENTRY-02/03 | 同上 | 修改单元格内容 → 确认输入可响应 |
| 复选框勾选联动按钮状态 | KB-ENTRY-04 | 同上 | 勾选 1 行 → 按钮变蓝；取消全选 → 按钮变灰 |
| 点击「存入知识库」成功提示 | KB-ENTRY-05 | 需要真实 bge-m3 模型环境 | 配置 CTRX_MODELS_DIR → 勾选行 → 点击 → 确认 ElMessage "已存入 N 条" |
| KB 不可用时橙色 el-alert 显示 | D-07 | 需要 503 响应场景 | 未配置模型环境下提交 → 确认橙色 el-alert 出现，按钮 disabled |
| PathB 不可用时 KB 区域隐藏 | D-08 | 需要手动触发不可用状态 | 使用无 PathB 数据的任务 → 确认 KB 录入区不可见 |

---

## 验证签字

- [ ] 所有任务有自动验证命令或 Wave 0 依赖
- [ ] 采样连续性：无连续 3 个任务无自动验证
- [ ] Wave 0 覆盖所有 MISSING 引用
- [ ] 无 watch-mode 标志
- [ ] 反馈延迟 < 30 秒
- [ ] `nyquist_compliant: true` 在 frontmatter 中设置

**审批：** 待审批
