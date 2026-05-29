# Phase 12: PyInstaller 打包 - Research

**Researched:** 2026-05-28  
**Domain:** PyInstaller `--onedir` packaging for FastAPI desktop backend  
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 使用**单一 spec + 平台参数化分支**，不拆 Windows/Linux 两套独立 spec。
- **D-02:** 打包默认**稳定优先**，禁用激进压缩/混淆；先保证可启动与可验收。
- **D-03:** `CTRX_DATA_DIR` / `CTRX_PORT` 的入口保持**desktop_main 单一入口**，不在 runtime hook 重复注入。
- **D-04:** 运行时缺失关键资源（如 `alembic/`、`dicts/`）时采用**fail-fast**，输出明确错误并阻断继续执行。
- **D-05:** hiddenimports 采用**宽覆盖已知模块一次到位**作为默认起步策略，优先减少干净机首轮失败。
- **D-06:** 对 `openai/httpx/uvicorn` 等动态导入链采用**手工维护锁定清单**，要求可审计。
- **D-07:** hiddenimports 在 spec 内按**平台分段**维护（Windows/Linux 可差异化）。
- **D-08:** 对 hiddenimports 变更启用**CI 差异门禁**，变更需有说明。
- **D-09:** `electron/resources` 默认只保留**最终可分发 onedir 产物**，不保留中间构建目录。
- **D-10:** 资源目录命名采用**带版本号目录**（例如 `ctrx-backend-win-x64-v1.2.0`）。
- **D-11:** 运行日志与临时文件放在**userData/CTRX_DATA_DIR 外置目录**，不写入安装资源目录。
- **D-12:** 旧版本资源清理策略为**保留当前 + 上一个版本**，支持快速回退。
- **D-13:** Phase 12 验收先覆盖**主链路最小烟测**：上传→抽取→下载。
- **D-14:** 烟测样本采用**固定 1 份黄金合同**，优先稳定可复现。
- **D-15:** 烟测失败默认**阻断发布**，不允许带风险放行。
- **D-16:** 验收沉淀采用**结构化 checklist + 命令 + 截图路径**。

### Claude's Discretion
- 具体 hiddenimports 清单条目与排序。
- spec 内平台分段的实现细节（条件表达式/辅助函数组织方式）。
- checklist 的字段模板与截图命名规范。

### Deferred Ideas (OUT OF SCOPE)
- 并发回归、校验层联动、path-b 细项验收扩展：可在后续阶段（Phase 13/14 或专项质量阶段）追加，不作为 Phase 12 阻断范围。

## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| PKG-01 | `desktop_main.py` 入口 + `CTRX_DATA_DIR/CTRX_PORT` + `cache_clear` + 程序化 Alembic + uvicorn + frozen 分支 | 启动链保持单入口；fail-fast 与 frozen 路径策略；spec 对应入口绑定 |
| PKG-02 | 完整 `--onedir` spec，hiddenimports 覆盖 uvicorn/sqlalchemy sqlite/pydantic_settings，datas 含 `dicts/`、`alembic/`，排除 `psycopg2`，产物落位 `electron/resources/` | 单 spec 平台分段模板；hiddenimports 审计清单；datas 收集与落位策略 |
| PKG-03 | 干净 Windows VM：上传→抽取→下载通过 | Clean VM 烟测方案、证据模板、发布阻断门禁 |

## Summary

Phase 12 的核心不是“能打包”，而是“可分发且可验收”：将 `desktop_main.py` 作为唯一入口，使用单一 spec 的平台分段维护方式，将 Python 运行时、动态导入链和必要数据资源一起固化到 `--onedir` 产物中。[VERIFIED: codebase][CITED: https://pyinstaller.org/en/stable/spec-files.html]

当前代码已满足 Phase 11 的关键前置：`desktop_main.py` 已具备程序化 Alembic 与 `get_settings.cache_clear()`；`backend/app/config.py` 已具备 `sys.frozen` / `_MEIPASS` 路径分支；`alembic/env.py` 已支持程序化 URL 注入；对应测试锚点在 `backend/tests/test_desktop_main.py` 已存在。[VERIFIED: codebase]

**Primary recommendation:** 采用“单 spec + 平台分段 + 宽覆盖 hiddenimports 起步 + datas fail-fast + Clean VM 证据化阻断发布”的组合策略，先锁定 PKG-03 成功率，再做 hiddenimports 收敛优化。[CITED: https://pyinstaller.org/en/stable/when-things-go-wrong.html]

## Project Constraints (from .cursor/rules/)

- 默认自动提交并推送 `master`，除非用户明确说“不要提交/仅本地”。[VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- 仅暂存与本次任务相关文件；禁止误纳入 `.env`、密钥、本地分析产物。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- export/extract 相关改动需跑相关 `pytest`。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]
- 规划文档改动要同步 `.planning/` 状态文件。 [VERIFIED: `contract_info/.cursor/rules/auto-commit-push.mdc`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| PyInstaller 构建编排（spec） | Packaging/Build Tier | Backend | 由构建定义决定模块收集与产物布局 |
| 运行时入口初始化（env + migration + uvicorn） | Backend Runtime Tier | Packaging/Build Tier | 业务入口在 `desktop_main.py`，spec 只负责携带依赖 |
| hiddenimports 审计与门禁 | Packaging/CI Tier | Backend Runtime Tier | 导入链由代码触发，但缺失检测在打包和 CI |
| 数据资源收集与 fail-fast | Packaging/Build Tier | Backend Runtime Tier | spec 决定是否携带；运行时负责缺失即失败 |
| 产物落位到 `electron/resources/` | Desktop Distribution Tier | Packaging/Build Tier | 供 Electron `extraResources` 消费 |
| Clean VM 烟测与证据沉淀 | QA/Release Tier | Desktop Tier | 验证“无 Python 环境可运行”这一发布性质 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---|---:|---|---|
| PyInstaller | 6.20.0 | `--onedir` 打包执行器 | 官方稳定版本，spec/hook/runtime 文档完善 [VERIFIED: pip index][CITED: https://pyinstaller.org/en/stable/spec-files.html] |
| uvicorn | installed 0.45.0 (latest 0.48.0) | ASGI 启动 | 项目既有依赖，运行入口已对齐 `uvicorn.run("backend.app.main:app")` [VERIFIED: codebase][VERIFIED: pip index] |
| httpx | installed 0.28.1 | LLM HTTP 客户端 | 代码直接使用 `httpx.AsyncClient`，需纳入 hiddenimports 审计 [VERIFIED: codebase][VERIFIED: pip index] |

### Supporting

| Library | Version | Purpose | When to Use |
|---|---:|---|---|
| PyInstaller hook utils | bundled with PyInstaller | `collect_submodules` / `collect_data_files` | 当手工清单维护成本变高时，用于生成审计候选清单 [CITED: https://pyinstaller.org/en/stable/hooks.html] |
| openai-python | latest 2.38.0 | OpenAI SDK（若后续替换为 SDK） | 当前项目未直接使用，但已被 D-06 锁定为审计对象 [VERIFIED: codebase][VERIFIED: pip index] |

## Architecture Patterns

### System Architecture Diagram

```text
PyInstaller build(spec)
    ├─ Analysis(entry=desktop_main.py, hiddenimports, datas, excludes)
    ├─ PYZ(pure python archive)
    ├─ EXE(ctrx-backend executable)
    └─ COLLECT(--onedir dist tree)
            │
            └─ copy to electron/resources/ctrx-backend-<platform>-v<version>/
                    │
Electron main process
    ├─ spawn backend executable
    ├─ set CTRX_DATA_DIR / CTRX_PORT
    └─ health-check /api/v1/health
                    │
desktop_main.py
    ├─ set DATABASE_URL (sqlite:///.../ctrx.db)
    ├─ get_settings.cache_clear()
    ├─ run_migrations(alembic upgrade head)
    ├─ fail-fast: assert alembic/dicts/templates exist
    └─ uvicorn.run(...)
                    │
User smoke flow (clean VM): upload -> extract -> download xlsx
```

### Pattern 1: 单 spec + 平台分段
**What:** 只维护一个 `ctrx_backend.spec`，在 spec 内按 `sys.platform` 做 `hiddenimports/datas/binaries` 分段。  
**When to use:** Windows/Linux 目标功能相同，仅运行时依赖有少量差异。  
**Example (recommended skeleton):**

```python
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(__file__).resolve().parent
IS_WIN = sys.platform.startswith("win")

common_hidden = [
    "sqlalchemy.dialects.sqlite",
    "pydantic_settings",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "httpx",
]
platform_hidden = ["colorama"] if IS_WIN else []
hiddenimports = common_hidden + platform_hidden

# Optional audit-only expansion candidates:
audit_candidates = collect_submodules("uvicorn")
```

Source: [CITED: https://pyinstaller.org/en/stable/spec-files.html], [CITED: https://pyinstaller.org/en/stable/hooks.html]

### Pattern 2: 数据资源收集 + 运行时 fail-fast
**What:** spec 明确 `datas` 收集 `alembic/`、`dicts/`、`templates/`；运行时开机即检查目录完整性，不满足即抛出明确异常。  
**When to use:** 冷启动必须依赖本地资源，且缺失时不可降级。  
**Example:**

```python
# in desktop_main.py (before run_migrations)
required_dirs = ["alembic", "dicts", "templates"]
for d in required_dirs:
    p = bundle_base / d
    if not p.is_dir():
        raise RuntimeError(f"Missing bundled resource directory: {p}")
```

Source: [VERIFIED: codebase], [CITED: https://pyinstaller.org/en/stable/usage.html]

### Anti-Patterns to Avoid
- **双 spec 漂移：** Windows/Linux 两份 spec 长期会分叉，违反 D-01。 [VERIFIED: CONTEXT]
- **运行时 hook 注入入口 env：** 会和 `desktop_main.py` 的单入口职责冲突，违反 D-03。 [VERIFIED: CONTEXT]
- **把日志/临时文件写到安装目录：** 会破坏可升级性与权限边界，违反 D-11。 [VERIFIED: CONTEXT]
- **烟测不证据化：** 无法形成发布阻断证据链，违反 D-16。 [VERIFIED: CONTEXT]

## Hiddenimports 审计清单与维护策略

### Baseline 清单（首版宽覆盖）

| Group | Modules (minimum) | Evidence |
|---|---|---|
| uvicorn dynamic chain | `uvicorn.logging`, `uvicorn.loops`, `uvicorn.loops.auto`, `uvicorn.protocols`, `uvicorn.protocols.http`, `uvicorn.protocols.http.auto`, `uvicorn.protocols.websockets`, `uvicorn.protocols.websockets.auto`, `uvicorn.lifespan`, `uvicorn.lifespan.on` | [CITED: https://pyinstaller.org/en/stable/when-things-go-wrong.html] + [VERIFIED: community recurring failures] |
| sqlite/runtime | `sqlalchemy.dialects.sqlite`, `pydantic_settings` | [VERIFIED: requirements + codebase imports] |
| llm/http | `httpx`, `httpcore`, `anyio` | `httpx` 为项目直接依赖，其余为常见运行链 [VERIFIED: pip metadata + codebase][ASSUMED] |
| openai compatibility lane | `openai`, `openai._client` | 当前代码未使用 openai SDK，但 D-06 明确纳入维护锁定清单 [VERIFIED: CONTEXT][VERIFIED: codebase] |

### 维护策略（可审计）
1. `pyinstaller --debug=imports` 作为首轮构建标准，记录 `ModuleNotFoundError` 证据。 [CITED: https://pyinstaller.org/en/stable/when-things-go-wrong.html]  
2. hiddenimports 维护分 3 层：`common_hidden`, `windows_hidden`, `linux_hidden`（对应 D-07）。 [VERIFIED: CONTEXT]  
3. 每次修改 hiddenimports，提交必须包含：
   - diff 摘要（新增/删除模块）  
   - 触发原因（报错栈或依赖变更）  
   - 回归结果（最小 smoke 通过）  
4. CI 增加“hiddenimports diff gate”：若变更该段但无说明文件（`docs/packaging/hiddenimports-changelog.md`），则失败。 [VERIFIED: CONTEXT][ASSUMED]

## 数据文件收集与 fail-fast 机制

### 必收集目录

| Path | Why required | Collected by |
|---|---|---|
| `alembic/` | 冷启动程序化迁移依赖 `env.py` 和 `versions/` | `datas` tuple |
| `dicts/` | 抽取/校验词典资源 | `datas` tuple |
| `templates/` | 导出模板与渲染资源 | `datas` tuple |

### 推荐 datas 定义

```python
datas = [
    (str(ROOT / "alembic"), "alembic"),
    (str(ROOT / "dicts"), "dicts"),
    (str(ROOT / "templates"), "templates"),
]
```

Source: [CITED: https://pyinstaller.org/en/stable/spec-files.html]

### fail-fast 触发条件
- 任一必需目录不存在：立即抛 `RuntimeError`，终止启动。 [VERIFIED: D-04]
- `run_migrations()` 找不到 `alembic_dir`：已有显式异常逻辑。 [VERIFIED: codebase]
- `DATABASE_URL` 非 sqlite 且未显式允许：直接阻断（避免误连 PostgreSQL）。 [ASSUMED]

## 产物落位到 `electron/resources/` 的命名与清理

### 命名建议
- Windows: `electron/resources/ctrx-backend-win-x64-v{appVersion}`
- Linux: `electron/resources/ctrx-backend-linux-x64-v{appVersion}`
- 可选加 build 号：`...-b{buildNumber}`（仅 CI 产物）[ASSUMED]

### 清理策略（与 D-12 对齐）
1. 拷贝新版本前，识别同平台历史目录。  
2. 保留：`current` + `previous`；删除更老版本。  
3. 生成 `electron/resources/.backend-manifest.json` 记录 `{platform, version, builtAt}` 供回退。 [ASSUMED]

### 回退操作（目标 < 5 分钟）
- 失败版本改名为 `.bad-<version>`  
- 将 `previous` 目录提升为 `current`（或重建软链接/配置指向）  
- 重跑 smoke 的 `health + upload + download` 最小链路

## Clean VM 烟测方案（PKG-03）

### Smoke 用例（Windows clean VM）

| Step | Command / Action | Expected |
|---|---|---|
| S1 | 启动 `ctrx-backend.exe`（无 Python 环境） | 无 `ModuleNotFoundError`，健康检查可达 |
| S2 | 调 `GET /api/v1/health` | 200 |
| S3 | 上传固定黄金合同 | 返回 job/file id |
| S4 | 执行抽取流程 | 状态 `done` 且无 fatal |
| S5 | 下载 xlsx | 200 且文件可打开 |
| S6 | 检查 `CTRX_DATA_DIR` | 数据仅落在指定目录 |

### 证据格式（D-16）

```text
evidence/phase12/
  smoke-checklist.md
  logs/
    backend-startup.log
    api-smoke.log
  screenshots/
    01-started.png
    02-health-200.png
    03-upload-ok.png
    04-extract-done.png
    05-download-ok.png
  artifacts/
    downloaded.xlsx
```

`smoke-checklist.md` 必填字段：
- VM 信息（OS 版本、是否装 Python=No）
- 二进制版本与 hash
- 执行命令
- 每步结果（PASS/FAIL）
- 失败栈摘要
- 执行人/时间戳

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | 运行数据位于 `CTRX_DATA_DIR`（db/uploads/exports） | 无迁移；仅验证目录隔离 [VERIFIED: codebase] |
| Live service config | Electron `extraResources` 将消费 `electron/resources/` | Phase 12 提供稳定目录命名 [VERIFIED: REQUIREMENTS/ROADMAP] |
| OS-registered state | None — verified by phase scope (packaging only) | 无 |
| Secrets/env vars | `CTRX_DATA_DIR`, `CTRX_PORT`, `DATABASE_URL` 启动时注入 | 保持入口单点在 `desktop_main.py` [VERIFIED: codebase] |
| Build artifacts | `dist/`, `build/`, `electron/resources/*` | 清理中间目录，保留 current+previous [VERIFIED: CONTEXT][ASSUMED] |

## Common Pitfalls

### Pitfall 1: hiddenimports 漏项只在干净机暴露
**What goes wrong:** 本地开发机可运行，clean VM 启动报 `ModuleNotFoundError`。  
**Why:** PyInstaller Analysis 无法覆盖动态导入链。 [CITED: https://pyinstaller.org/en/stable/when-things-go-wrong.html]  
**How to avoid:** `--debug=imports` + 宽覆盖起步 + CI diff gate。  
**Warning signs:** `uvicorn.*` 或 `httpx.*` 子模块缺失报错。

### Pitfall 2: datas 收集了目录但运行时路径不一致
**What goes wrong:** `alembic/` 打进包了，但 `bundle_base` 拼接路径错误。  
**Why:** `sys._MEIPASS` / `__file__` 逻辑混用不一致。 [CITED: https://pyinstaller.org/en/latest/runtime-information.html]  
**How to avoid:** 统一使用已存在的 `_get_bundle_base()` / `_bundle_base()` 模式。 [VERIFIED: codebase]

### Pitfall 3: 产物目录累积污染导致回退不可控
**What goes wrong:** `electron/resources/` 存在多代目录且无清单，Electron 引用错版本。  
**How to avoid:** 版本化命名 + manifest + 保留 2 代策略。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| 动态导入探测 | 自写 AST 扫描器 | PyInstaller `--debug=imports` + hiddenimports + hooks | 官方路径可观测且可复现 [CITED: https://pyinstaller.org/en/stable/when-things-go-wrong.html] |
| 包内数据遍历 | 手写复制脚本逻辑散落多处 | spec `datas` / `collect_data_files` | 规范化、跨平台一致 [CITED: https://pyinstaller.org/en/stable/spec-files.html] |
| 多平台 spec 管理 | 两份 spec 并行维护 | 单 spec 平台分段 | 减少漂移，符合 D-01 [VERIFIED: CONTEXT] |

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (`pytest.ini` 已存在) |
| Config file | `contract_info/pytest.ini` |
| Quick run command | `pytest backend/tests/test_desktop_main.py -q -x` |
| Full suite command | `pytest backend/tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| PKG-01 | 启动链入口行为（cache_clear + migration） | unit/integration | `pytest backend/tests/test_desktop_main.py -q -x` | ✅ |
| PKG-02 | spec hiddenimports/datas/excludes 正确性 | build smoke | `pyinstaller ctrx_backend.spec --noconfirm --clean` | ❌ Wave 0 |
| PKG-03 | clean VM 上传→抽取→下载 | manual smoke (gated) | `powershell scripts/smoke_phase12.ps1` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `ctrx_backend.spec`（单 spec + 平台分段）
- [ ] `scripts/package_backend.ps1` / `scripts/package_backend.sh`
- [ ] `scripts/smoke_phase12.ps1`（结构化日志输出）
- [ ] `docs/packaging/hiddenimports-changelog.md`

## Security Domain

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V5 Input Validation | yes | 继续复用既有 API 校验，不在打包层新增输入面 |
| V6 Cryptography | no | 本阶段无加密算法新增 |
| V14 Config | yes | 环境变量仅通过桌面入口注入，避免 runtime hook 注入漂移 |

## Risks and Rollback

### Top Risks
1. **R1: hiddenimports 首轮不足**（影响：clean VM 启动失败）  
   Mitigation: 宽覆盖起步 + `--debug=imports` + smoke gate。  
2. **R2: datas 漏收导致启动即崩**（影响：迁移/抽取不可用）  
   Mitigation: 启动 fail-fast + 目录存在性断言。  
3. **R3: 资源目录版本管理混乱**（影响：Electron 引用错误二进制）  
   Mitigation: 版本化命名 + manifest + current/previous 保留策略。  

### Rollback Plan
- 触发条件：PKG-03 任一步骤 FAIL。  
- 回滚动作：
  1) 切换到 `electron/resources` 的 previous 版本目录；  
  2) 标记当前版本 `.bad-*`；  
  3) 复跑最小 smoke（health/upload/download）；  
  4) 阻断发布并记录失败证据。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `httpcore/anyio` 需要显式 hiddenimports | Hiddenimports audit | 若不需要则冗余；若需要且缺失会 runtime fail |
| A2 | 使用 manifest 管理 `current/previous` 最稳妥 | Artifact strategy | 若 Electron 侧已有强绑定策略，需要改为对齐其读取方式 |
| A3 | `scripts/smoke_phase12.ps1` 可作为统一证据入口 | Validation | 若团队不接受脚本化 smoke，需要转人工 checklist-only |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | 构建与本地验证 | ✓ | 3.11.9 | — |
| PyInstaller | PKG-02 构建 | ✗ | — | 临时 `pip install pyinstaller==6.20.0` |
| Node.js | Electron 资源对接 | ✓ | v22.22.0 | — |
| npm | Electron 构建链 | ✓ | 11.12.1 | — |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- PyInstaller 未安装：可通过项目 venv 安装后继续。 [VERIFIED: shell]

## Sources

### Primary (HIGH confidence)
- [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html) — `Analysis/PYZ/EXE/COLLECT` 与 `--onedir` 结构。
- [PyInstaller runtime information](https://pyinstaller.org/en/latest/runtime-information.html) — `sys.frozen` / `sys._MEIPASS` 运行时语义。
- [PyInstaller when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html) — hidden imports 检测与 `--debug=imports`。
- [PyInstaller hooks](https://pyinstaller.org/en/stable/hooks.html) — `collect_submodules` / `collect_data_files`。
- Project code anchors: `desktop_main.py`, `backend/app/config.py`, `alembic/env.py`, `backend/tests/test_desktop_main.py`.

### Secondary (MEDIUM confidence)
- [Uvicorn settings/docs](https://uvicorn.dev/settings/) — 动态协议组件与 extras。
- [OpenAI PyPI page](https://pypi.org/project/openai/) — SDK 与 httpx 关系（用于 D-06 审计上下文）。

### Tertiary (LOW confidence)
- 社区 Q&A 中关于 uvicorn hiddenimports 的常见清单（用于补充首轮宽覆盖，不作为唯一依据）。

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH（官方文档 + pip 索引 + 代码锚点）
- Architecture: HIGH（已锁定决策 + 现有入口代码已就位）
- Pitfalls: MEDIUM（部分来自社区复现模式，已由官方机制校验）

**Research date:** 2026-05-28  
**Valid until:** 2026-06-27
