# Phase 23: PyInstaller 打包兼容与烟测 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 23-PyInstaller 打包兼容与烟测
**Areas discussed:** hiddenimports 边界与门禁, 离线模型打包布局, 运行时环境变量绑定, 烟测契约

---

## hiddenimports 边界与门禁

| Option | Description | Selected |
|--------|-------------|----------|
| 最小增量 | 仅补 LanceDB/pyarrow/sentence-transformers 缺口 | ✓ |
| 显式全量 | 显式列举所有已知 hiddenimports | |
| 混合 | 核心最小增量 + 可选依赖全量 | |

**User's choice:** 最小增量

---

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 Windows | Windows 先收口 | ✓ |
| Windows+Linux | 同时处理两平台 | |
| Windows 优先 Linux 标注 | Windows 完整处理，Linux 仅标注待办 | |

**User's choice:** 仅 Windows

---

| Option | Description | Selected |
|--------|-------------|----------|
| 严格阻断 | hiddenimports 变更必须同步 changelog，否则 CI 阻断 | ✓ |
| 仅告警 | 变更不同步时仅 warning，不阻断 | |
| 人工审核 | 门禁脚本输出报告，人工确认后合并 | |

**User's choice:** 严格阻断

---

| Option | Description | Selected |
|--------|-------------|----------|
| 阻断发布 | 出现 ModuleNotFoundError 不发布 | ✓ |
| 带已知问题发布 | 记录问题后发布 | |
| 下版本 hotfix | 本次发布，下版本修复 | |

**User's choice:** 阻断发布

---

## 离线模型打包布局

| Option | Description | Selected |
|--------|-------------|----------|
| 版本化目录并列放置 | `electron/resources/models/<model-id-or-version>/` | ✓ |
| 扁平目录 | `electron/resources/models/` 直接存放权重文件 | |
| 放入后端包目录 | 将模型权重放入 ctrx-backend 产物目录 | |

**User's choice:** `electron/resources/models/<model-id-or-version>/`

---

| Option | Description | Selected |
|--------|-------------|----------|
| 固定单活版本 | 包内只有一个 bge-m3 版本 | ✓ |
| 同包多版本 | 同时打包多个模型版本供切换 | |
| latest 别名 | 用 `latest` 软链指向当前版本 | |

**User's choice:** 固定单活版本

---

| Option | Description | Selected |
|--------|-------------|----------|
| 安装包强制内置 | 打包时模型权重已在包内 | ✓ |
| 首次下载 | 安装后首次启动时从网络拉取 | |
| 混合策略 | 包内预置小模型，大模型首次下载 | |

**User's choice:** 安装包强制内置

---

| Option | Description | Selected |
|--------|-------------|----------|
| 快速失败并明确报错 | 模型目录缺失/损坏时报错退出 | ✓ |
| 静默降级 | 模型不可用时 KB 功能静默降级（参考 Phase 20 D-06） | |
| 自动补拉 | 缺失时自动从网络下载 | |

**User's choice:** 快速失败并明确报错（Electron 层面检测 extraResources 中目录完全缺失；Python 运行时模型加载失败仍遵循 Phase 20 D-06 软降级）

---

## 运行时环境变量绑定

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 Electron 主进程注入 | 主进程统一设置环境变量后 spawn 后端 | ✓ |
| 主进程 + desktop_main 兜底 | 主进程注入，Python 入口再次检查 | |
| 后端自解析 | Python 后端根据 sys._MEIPASS 自行推导路径 | |

**User's choice:** 仅 Electron 主进程注入

---

| Option | Description | Selected |
|--------|-------------|----------|
| 每次 spawn/restart 都注入 | 每次后端子进程启动时都设置环境变量 | ✓ |
| 仅首次启动 | 只在应用初次启动时注入 | |
| 仅保存设置时 | 只在用户保存 Settings 后注入 | |

**User's choice:** 每次 spawn/restart 都注入

---

| Option | Description | Selected |
|--------|-------------|----------|
| manifest 驱动 | 从 `.backend-manifest.json` + extraResources 路径推导 | ✓ |
| 硬编码路径 | 固定 `resources/models/bge-m3` 字符串 | |
| Settings 可配 | 用户在设置页自定义模型路径 | |

**User's choice:** manifest + resources 相对路径推导

---

| Option | Description | Selected |
|--------|-------------|----------|
| 应用路径覆盖系统值 | 应用注入的路径优先于系统环境变量 | ✓ |
| 系统优先 | 若系统已有该变量则不覆盖 | |
| 冲突即中止 | 检测到冲突时报错退出 | |

**User's choice:** 应用路径覆盖系统值

---

## 烟测契约

| Option | Description | Selected |
|--------|-------------|----------|
| 纯手动清单 | 文字步骤，任何人可跟随操作 | ✓ |
| 脚本演示 + 手动确认 | 脚本触发 API，UI 部分手动检查 | |
| 自动化端到端测试 | Playwright 驱动 Electron | |

**User's choice:** 纯手动清单

---

通过标准（multiSelect）:

| 标准 | 选中 |
|------|------|
| KB 录入成功提示（「已存入 N 条」ElMessage） | ✓ |
| 知识库配置页可见该条目 | ✓ |
| 重新处理合同后 PathB RAG 注入可查（后端日志关键字） | ✓ |
| 后端启动日志无 ModuleNotFoundError | ✓ |

**User's choice:** 全部四项

---

| Option | Description | Selected |
|--------|-------------|----------|
| 后端日志验证 | 日志含 "RAG context" 或 "few-shot" 关键字 | ✓ |
| debug/verify 接口 | 专用 /kb/debug 端点返回检索详情 | |
| 信任现有单元测试 | 单测已覆盖，烟测不重复证明 | |

**User's choice:** 后端日志验证

---

| Option | Description | Selected |
|--------|-------------|----------|
| 阻断发布 | 烟测失败不发布 | ✓ |
| 记录已知问题并发布 | 记录后仍发布 | |
| 人工判断 | 由项目负责人逐项决定 | |

**User's choice:** 阻断发布

---

## Claude's Discretion

- 具体 hiddenimports 条目（lancedb 子模块完整列表、pyarrow 版本绑定）由 researcher 审计 `.venv` 得出
- extraResources `from`/`to` 字段格式由 planner 参考 Phase 12/14 先例确认
- hiddenimports changelog 文件路径与格式由 planner 确认（脚本 `--changelog` 参数）
- Electron 主进程中检测模型目录缺失的具体时机与报错方式由 planner 设计

## Deferred Ideas

- Linux 打包兼容（`linux_hidden` 列表 + AppImage 烟测）→ 下一里程碑
- 烟测自动化（Playwright）→ 超出当前内部工具需求
- 模型权重在线更新 → 超出 v1.4 范围
