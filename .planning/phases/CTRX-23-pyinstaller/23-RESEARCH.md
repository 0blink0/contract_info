# Phase 23: PyInstaller 打包兼容与烟测 - Research

**Researched:** 2026-06-02
**Domain:** PyInstaller hiddenimports expansion + offline model packaging + smoke testing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**hiddenimports 边界与门禁**
- D-01: 最小增量策略 — 仅在 `ctrx_backend.spec` 补充 LanceDB/pyarrow/sentence-transformers 缺口，不做全量显式列举。现有条目保持不变。
- D-02: 平台范围：仅 Windows 收口（`windows_hidden` 列表）；Linux 标注为下一里程碑任务，暂不阻断本阶段。
- D-03: 严格门禁：`scripts/check_hiddenimports_diff.py` 已在项目中，hiddenimports 变更必须同步更新 changelog（门禁脚本比较 spec 与 changelog diff）；changelog 未更新时阻断 CI/PR。
- D-04: 打包产物出现 `ModuleNotFoundError` → 阻断发布，不带已知问题发布。

**离线模型打包布局**
- D-05: 模型权重目录放置于 `electron/resources/models/bge-m3/`（版本化子目录），随 extraResources 打入安装包。
- D-06: 固定单活版本 — 包内仅保留当前使用的 bge-m3 版本，不做多版本并存。
- D-07: 安装包强制内置模型权重 — 不做首次启动下载逻辑；模型必须在打包时已就位。
- D-08: 模型目录缺失或损坏时（Electron 层面检查）：快速失败并输出明确错误信息，不静默降级。（注意：与 Phase 20 D-06 不矛盾——Phase 20 的软降级处理的是 Python 运行时模型加载失败；D-08 处理的是 Electron 主进程发现 extraResources 中模型目录完全不存在的情况。）

**运行时环境变量绑定**
- D-09: 仅 Electron 主进程负责注入 `SENTENCE_TRANSFORMERS_HOME`、`TRANSFORMERS_CACHE`、`CTRX_MODELS_DIR`；后端不做自解析。
- D-10: 每次 spawn/restart 后端子进程时均注入上述变量（不限于首次启动）。
- D-11: 模型路径由 manifest（`.backend-manifest.json`）+ extraResources 相对路径推导，不硬编码绝对路径。
- D-12: 若系统已有同名环境变量（如 `TRANSFORMERS_CACHE`），应用注入值覆盖系统值。

**烟测契约**
- D-13: 执行方式：纯手动清单 — 一份可跟随操作的文字步骤，任何人可在已安装的打包产物上执行。不做 Playwright/自动化。
- D-14: 通过标准（四项全达到方算通过）：
  1. 后端启动日志无 `ModuleNotFoundError`（embedding 模型加载行可见）
  2. PathB 页录入并提交后出现「已存入 N 条」 `ElMessage.success` 提示
  3. 知识库配置页刷新后可见该新录入条目
  4. 重新处理一份含业绩报酬条款的合同后，后端日志包含 `RAG context` 或 `few-shot` 关键字（证明注入块已构造）
- D-15: RAG 注入验证方式：后端日志关键字（不需要额外 debug 接口）。
- D-16: 烟测失败时阻断发布 — 与 hiddenimports 门禁策略一致。

### Claude's Discretion

- 具体 hiddenimports 条目（lancedb 子模块完整列表、pyarrow 版本绑定、sentence-transformers 依赖链）由 researcher 从已安装的 `.venv` 和 lancedb 文档中审计，planner 整理成最终列表。
- extraResources 在 `package.json` electron-builder 配置中的 `from`/`to` 字段格式由 planner 确认，参考 Phase 12/14 已有模式。
- `check_hiddenimports_diff.py` 对应的 changelog 文件路径与格式由 planner 确认（脚本已存在，可能需要创建对应 changelog 文件）。

### Deferred Ideas (OUT OF SCOPE)

- Linux 打包兼容（`linux_hidden` 列表 + AppImage 烟测）→ 下一里程碑
- 烟测自动化（Playwright 驱动 Electron 全链路）→ 超出内部工具当前需求
- 模型权重在线更新机制 → 超出 v1.4 范围

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KB-PKG-01 | LanceDB 相关包（`lancedb`、`pyarrow` 等）纳入 PyInstaller `hiddenimports` 清单与打包 spec | hiddenimports 增量清单已确定；lancedb/pyarrow 均需先安装到 .venv |
| KB-PKG-02 | sentence-transformers 模型权重目录（离线缓存）打包至 `extraResources`，应用启动时通过 `TRANSFORMERS_CACHE` / `SENTENCE_TRANSFORMERS_HOME` 路径变量指向该目录 | Electron main.ts 注入点已定位；extraResources 格式已知；模型目录布局已明确 |
| KB-PKG-03 | 烟测验证打包产物的知识库全链路：入库（含 embedding 生成）→ LanceDB 持久化 → 语义检索 → RAG prompt 注入，全流程无异常 | 烟测清单结构参考 Phase 12 模板；log 关键字已明确 |

</phase_requirements>

## Summary

Phase 23 需要解决三个独立但相互依赖的打包工程问题。第一，当前 `.venv` 中**未安装** `lancedb`、`pyarrow`、`sentence-transformers`，这是所有后续工作的前置阻塞项——必须先安装依赖，才能审计 hiddenimports 缺口。第二，`kb_service.py` 使用 bge-m3 模型，通过 `SentenceTransformer(str(model_path), local_files_only=True)` 加载，`model_path = Path(CTRX_MODELS_DIR) / "bge-m3"`；Electron 主进程需要在 `backendChildEnv()` 中同时注入 `CTRX_MODELS_DIR`、`SENTENCE_TRANSFORMERS_HOME`、`TRANSFORMERS_CACHE` 三个变量。第三，烟测清单以 Phase 12 模板为蓝本扩展 KB 全链路，通过日志关键字（`RAG context` / `few-shot`）验证 RAG 注入。

当前项目状态：`ctrx_backend.spec` 存在且有 `common_hidden`/`windows_hidden` 结构；`docs/packaging/hiddenimports-changelog.md` 已存在（内容为 Phase 12 基线）；`check_hiddenimports_diff.py` 使用 git diff 检测，发现 spec 变更但 changelog 无变更时返回退出码 1；changelog 路径固定为 `docs/packaging/hiddenimports-changelog.md`（已由 CI workflow 确认）。`electron/resources/models/` 目录**不存在**，需在打包前创建并下载 bge-m3 权重。

**Primary recommendation:** Wave 0 安装依赖 + 下载模型 → Wave 1 扩充 hiddenimports + extraResources 配置 + Electron 注入 → Wave 2 重新打包 + 手动烟测清单执行。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| lancedb/pyarrow hiddenimports 扩充 | Packaging/Build Tier | — | 由 ctrx_backend.spec 控制，PyInstaller 打包时引入 |
| sentence-transformers hiddenimports 扩充 | Packaging/Build Tier | — | 同上；sentence-transformers 依赖链（torch/tokenizers/transformers）均需显式声明 |
| 模型权重文件分发 | Desktop Distribution Tier | Packaging/Build Tier | electron-builder extraResources 负责将 `electron/resources/models/` 打入安装包 |
| 运行时模型路径注入 | Electron Main Process | — | `backendChildEnv()` 统一注入；后端仅消费 env var，不自解析路径 |
| 模型加载与 embedding 生成 | Backend Runtime Tier | — | `kb_service.py` 通过 `CTRX_MODELS_DIR` 加载 bge-m3 |
| 烟测门禁决策 | QA/Release Tier | — | 手动执行，四项通过标准缺一不可 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyInstaller | 6.20.0 [ASSUMED] | 打包 | 项目已选定，Phase 12 沿用 |
| lancedb | >=0.33.0 (requirements.txt) | 向量数据库 hiddenimports | KB 核心依赖 [CITED: requirements.txt] |
| pyarrow | lancedb 依赖 | Arrow 格式支持 | lancedb 内部依赖，需同步纳入 hiddenimports [ASSUMED] |
| sentence-transformers | >=5.5.1 (requirements.txt) | embedding 模型 | KB embedding 生成 [CITED: requirements.txt] |
| bge-m3 | 本地离线权重 | 中文语义检索模型 | `kb_service.py` 硬编码路径 `Path(CTRX_MODELS_DIR)/"bge-m3"` [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torch | sentence-transformers 依赖 | PyTorch 运行时 | 打包时需枚举子模块确保 hiddenimports 完整 [ASSUMED] |
| tokenizers | sentence-transformers 依赖 | HuggingFace tokenizer | lancedb/sentence-transformers 均使用 [ASSUMED] |
| transformers | sentence-transformers 依赖 | HuggingFace transformers | sentence-transformers 依赖链 [ASSUMED] |
| huggingface-hub | sentence-transformers 依赖 | 模型缓存结构 | 离线模式下缓存目录格式由此决定 [ASSUMED] |

**Installation (Wave 0 prerequisite):**
```bash
# 在 .venv 中安装 — 这是 Phase 23 的前置阻塞项
pip install lancedb>=0.33.0 sentence-transformers>=5.5.1
# pyarrow 由 lancedb 作为依赖自动安装
```

**Version verification:**
```bash
pip show lancedb sentence-transformers pyarrow torch
```

## Package Legitimacy Audit

> Note: lancedb, sentence-transformers, pyarrow, torch are NOT currently installed in `.venv`. They are in `requirements.txt` and have known track records as widely-used production libraries. slopcheck could not run on uninstalled packages.

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| lancedb | PyPI | ~3 yrs | github.com/lancedb/lancedb | [ASSUMED OK] | Approved — well-known vector DB library |
| pyarrow | PyPI | ~9 yrs | github.com/apache/arrow | [ASSUMED OK] | Approved — Apache Arrow, widely used |
| sentence-transformers | PyPI | ~6 yrs | github.com/UKPLab/sentence-transformers | [ASSUMED OK] | Approved — widely used NLP library |
| torch | PyPI | ~8 yrs | github.com/pytorch/pytorch | [ASSUMED OK] | Approved — Meta PyTorch |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable for uninstalled packages; all packages are `[ASSUMED]` based on known ecosystem standing. After Wave 0 install, run `slopcheck install lancedb sentence-transformers pyarrow` to verify.*

## Architecture Patterns

### System Architecture Diagram

```text
Wave 0 — 依赖安装 & 模型下载
  pip install lancedb sentence-transformers     → .venv 就位
  python -c "from sentence_transformers ..."   → 下载 bge-m3 到本地缓存
  cp <cache>/bge-m3 electron/resources/models/bge-m3/

Wave 1 — 配置变更
  ctrx_backend.spec
    windows_hidden += [lancedb.*, pyarrow.*, sentence_transformers.*, torch.*]
  docs/packaging/hiddenimports-changelog.md    → 追加变更条目 (D-03 门禁)
  package.json build.extraResources
    += { from: "electron/resources/models", to: "electron/resources/models" }
  electron/main.ts  backendChildEnv()
    += CTRX_MODELS_DIR / SENTENCE_TRANSFORMERS_HOME / TRANSFORMERS_CACHE

Wave 2 — 重新打包 & 烟测
  scripts/build.ps1 -Version 1.4.0             → Step 1 pyinstaller + copy
  electron-builder --win                        → 含 extraResources 打包
  手动安装 CTRX-Setup-1.4.0.exe（无 Python 环境机器）
  执行 docs/smoke-test-23.md 全链路清单
```

### Recommended Project Structure Changes

```
electron/
└── resources/
    ├── .backend-manifest.json         # 已存在
    ├── ctrx-backend-win-x64-v1.4.0/  # Wave 1 重新打包后
    └── models/                        # Wave 0 新建
        └── bge-m3/                    # bge-m3 权重目录（~2GB）
docs/
├── packaging/
│   ├── hiddenimports-changelog.md     # 追加 Phase 23 变更条目
│   └── smoke-test-23.md              # 新建（烟测清单）
```

### Pattern 1: hiddenimports 增量扩充策略 (D-01)

**What:** 在现有 `windows_hidden` 列表追加新包；`common_hidden` 保持不变（lancedb/pyarrow/sentence-transformers 仅在 Windows 验收范围内，符合 D-02）。

**When to use:** 依赖安装完成后，通过 `pyinstaller --debug=imports` 观察 `ModuleNotFoundError`，最小增量补入 `windows_hidden`。

**Example (spec 扩充骨架):**
```python
# Source: [VERIFIED: codebase — ctrx_backend.spec] extended per D-01
windows_hidden = [
    "colorama",
    # lancedb — 动态导入链
    "lancedb",
    "lancedb.remote",
    "lancedb.embeddings",
    # pyarrow — C 扩展子模块
    "pyarrow",
    "pyarrow.vendored",
    "pyarrow.vendored.version",
    # sentence-transformers
    "sentence_transformers",
    "sentence_transformers.models",
    "sentence_transformers.util",
    # torch (CPU minimal)
    "torch",
    "torch.utils",
    "torch.utils.data",
    # tokenizers / transformers
    "tokenizers",
    "transformers",
    "transformers.models",
    "transformers.models.bert",
    "transformers.models.xlm_roberta",
    # huggingface_hub (offline mode)
    "huggingface_hub",
    "huggingface_hub.file_download",
]
```

> **Note:** The list above is `[ASSUMED]` — actual required entries must be determined by running `pyinstaller --debug=imports` after Wave 0 install. The entries with the highest risk of being missed by PyInstaller's static analysis are dynamic-import-heavy submodules. The actual minimal set will be confirmed by build testing.

### Pattern 2: Electron 环境变量注入扩展 (D-09, D-10, D-11)

**What:** 在 `backendChildEnv()` 中推导 `resourcesPath` 并注入三个模型路径变量。所有三个变量指向同一目录（`<resourcesPath>/electron/resources/models`），因为：
- `CTRX_MODELS_DIR` — 被 `kb_service.py` 读取，`model_path = Path(CTRX_MODELS_DIR) / "bge-m3"`
- `SENTENCE_TRANSFORMERS_HOME` — sentence-transformers 缓存根目录（在此目录下查找 `<model-id>/`）
- `TRANSFORMERS_CACHE` — HuggingFace transformers 兼容缓存路径

**Key insight:** `resourcesPath` 在 packed 模式和 dev 模式下来源不同：
- Packed: `process.resourcesPath` （Electron 注入，指向安装包 resources 目录）
- Dev: 需手动推导为 `path.join(__dirname, '..', 'electron', 'resources')` 或类似路径

**Example (main.ts backendChildEnv 扩展):**
```typescript
// Source: [VERIFIED: codebase — electron/main.ts backendChildEnv()]
function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  const ragTopK = Number.isInteger(settings.ragTopK) ? settings.ragTopK : 3

  // Derive resourcesPath: packed mode uses process.resourcesPath,
  // dev mode falls back to the manifest-resolved resourcesDir
  const resourcesDir = resolveResourcesDir()  // reuse existing backendEntrypoint() logic
  const modelsDir = path.join(resourcesDir, 'models')

  return {
    ...process.env,          // spread first (D-12: injected values override system env)
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    OPENAI_API_KEY: settings.llmApiKey.trim(),
    OPENAI_BASE_URL: settings.llmBaseUrl.trim(),
    LLM_MODEL: settings.llmModel.trim(),
    RAG_TOP_K: String(ragTopK),
    // Phase 23 additions
    CTRX_MODELS_DIR: modelsDir,
    SENTENCE_TRANSFORMERS_HOME: modelsDir,
    TRANSFORMERS_CACHE: modelsDir,
  }
}
```

> Note: The spread of `...process.env` followed by explicit keys means the explicit keys WIN (override system env), satisfying D-12. [VERIFIED: JavaScript object spread semantics]

### Pattern 3: extraResources 格式扩展 (D-05)

**What:** 在 `package.json` `build.extraResources` 中追加 models 目录条目。

**Existing format confirmed:**
```json
// Source: [VERIFIED: codebase — package.json]
"extraResources": [
  {
    "from": "electron/resources",
    "to": "electron/resources",
    "filter": [
      "ctrx-backend-*/**",
      "ctrx-backend-*",
      ".backend-manifest.json"
    ]
  }
]
```

**Extension option A — add models filter to existing entry:**
```json
"filter": [
  "ctrx-backend-*/**",
  "ctrx-backend-*",
  ".backend-manifest.json",
  "models/**"
]
```

**Extension option B — separate entry:**
```json
{
  "from": "electron/resources/models",
  "to": "electron/resources/models",
  "filter": ["**/*"]
}
```

> D-05 says models go at `electron/resources/models/bge-m3/`. Option A (adding `"models/**"` to the existing filter glob) is minimal and consistent with the established pattern. Option B is also valid. The planner should pick based on clarity preference — both are functionally equivalent. [ASSUMED]

### Pattern 4: hiddenimports 门禁流程 (D-03)

**check_hiddenimports_diff.py behavior confirmed:** [VERIFIED: codebase — scripts/check_hiddenimports_diff.py]
- Uses `git diff --name-only <base> -- <spec>` to detect changes in `common_hidden`, `windows_hidden`, `linux_hidden`, `hiddenimports` tokens.
- If spec changed but changelog not changed → exit code 1.
- If changelog does not exist AND spec not changed → gate passes (returns 0).
- **Changelog path used by CI:** `docs/packaging/hiddenimports-changelog.md` [VERIFIED: codebase — .github/workflows/backend-packaging-gate.yml]
- **Changelog file EXISTS** at `docs/packaging/hiddenimports-changelog.md` with Phase 12 baseline entry [VERIFIED: codebase].

**Gate invocation (local + CI):**
```bash
python scripts/check_hiddenimports_diff.py \
  --base origin/master \
  --spec ctrx_backend.spec \
  --changelog docs/packaging/hiddenimports-changelog.md
```

Phase 23 must append a changelog entry in the same commit as the spec change.

### Anti-Patterns to Avoid

- **Adding lancedb to `common_hidden` instead of `windows_hidden`:** D-02 says Windows-only scope for this phase. Linux deferred.
- **Changing resourcesPath derivation to hardcoded path:** D-11 forbids hardcoded absolute paths; use manifest + app.getPath('userData') pattern.
- **Setting SENTENCE_TRANSFORMERS_HOME without also setting TRANSFORMERS_CACHE:** Some versions of sentence-transformers check both; set all three for robustness [ASSUMED].
- **Assuming model directory already exists:** `electron/resources/models/` does NOT exist currently — Wave 0 must create it and populate bge-m3 weights [VERIFIED: codebase filesystem scan].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| lancedb 动态导入探测 | 手写 import 扫描器 | `pyinstaller --debug=imports` + 逐步追加 `windows_hidden` | 官方调试路径，错误可复现 [CITED: pyinstaller.org/en/stable/when-things-go-wrong.html] |
| 模型下载与缓存格式 | 自写 HuggingFace HTTP 客户端 | `sentence-transformers` 标准下载 → 复制缓存目录 | 缓存格式由 huggingface_hub 维护，手写会偏离 `local_files_only=True` 期望的目录结构 [ASSUMED] |
| resourcesPath 推导 | 重新写路径查找逻辑 | 复用 `backendEntrypoint()` 内的 `resourcesCandidates` + `.backend-manifest.json` 模式 | 已有路径查找逻辑，manifest 提供 current.path 字段 [VERIFIED: codebase] |
| 烟测脚本自动化 | Playwright / 脚本 | 手动 checklist (D-13) | 决策已锁定；自动化在本阶段 OUT OF SCOPE |

**Key insight:** lancedb 使用 Rust 扩展（`lancedb._lib`）和 pyarrow C 扩展，PyInstaller 静态分析无法覆盖所有动态加载路径。`--debug=imports` 是唯一可靠方式来发现实际缺口。

## Critical Pre-conditions (Wave 0 Blockers)

以下两项是阻塞后续所有工作的前置条件，必须作为 Wave 0 的独立任务：

### Blocker 1: 依赖安装
```bash
# lancedb 和 sentence-transformers 当前未在 .venv 中安装
# VERIFIED: pip list 未见 lancedb/pyarrow/sentence-transformers/torch
pip install lancedb>=0.33.0 sentence-transformers>=5.5.1
# 验证
pip show lancedb pyarrow sentence-transformers torch
```

### Blocker 2: bge-m3 模型权重下载
```python
# 下载 bge-m3 到本地缓存，然后复制到 electron/resources/models/bge-m3/
from sentence_transformers import SentenceTransformer
import shutil, os
model = SentenceTransformer("BAAI/bge-m3")  # 首次下载 (~2.5GB)
# 模型缓存在 ~/.cache/huggingface/hub/models--BAAI--bge-m3/
# 或 sentence-transformers 格式: ~/.cache/torch/sentence_transformers/BAAI_bge-m3/
```

**Key finding:** `kb_service.py` 使用的模型路径为 `Path(CTRX_MODELS_DIR) / "bge-m3"`，即 `local_files_only=True` + 直接路径模式。因此模型目录结构需匹配 SentenceTransformer 从本地路径加载的预期格式（不是 huggingface hub 缓存格式，而是直接 model directory 格式，包含 `config.json`、`tokenizer.json`、`pytorch_model.bin` 或 `model.safetensors`）。[VERIFIED: codebase — kb_service.py line 181: `SentenceTransformer(str(model_path), local_files_only=True)`]

**模型大小估计:** bge-m3 约 2.5GB（包含多精度权重）[ASSUMED]，对安装包体积影响显著。

### Blocker 3: 确认实际 hiddenimports 缺口
只有在 Blocker 1 完成后，才能运行 `pyinstaller --debug=imports` 得到真实的缺口清单。Phase 12 的经验表明，宽覆盖起步比保守起步更安全（D-05 沿用该策略）。

## Common Pitfalls

### Pitfall 1: sentence-transformers 缓存目录格式 vs. 直接模型目录格式

**What goes wrong:** 复制 `~/.cache/huggingface/hub/models--BAAI--bge-m3/` 作为 `electron/resources/models/bge-m3/`，但 `SentenceTransformer(path, local_files_only=True)` 加载失败（目录结构不匹配）。

**Why it happens:** HuggingFace hub 缓存格式是 `models--<org>--<model>/blobs/` + `refs/` + `snapshots/` 树，而 `SentenceTransformer(local_path)` 期望的是展平的 model directory（`config.json` 在根目录）。

**How to avoid:** 先下载模型，然后使用 `model.save('/path/to/bge-m3')` 导出为标准 model directory 格式，或使用 `snapshot_download` 后正确展平目录。[ASSUMED — based on sentence-transformers documentation conventions]

**Warning signs:** 启动日志出现 `OSError: Can't load config for 'bge-m3'` 或 `ValueError: 'bge-m3' doesn't have any configuration for local paths`.

### Pitfall 2: pyarrow DLL 依赖未被 hiddenimports 覆盖

**What goes wrong:** pyarrow 内部有多个 C 扩展子模块（`pyarrow._parquet`, `pyarrow.lib`, `pyarrow._arrow_cffi` 等），PyInstaller 的静态分析可能漏掉其中几个，导致 clean VM 上出现 `ImportError` 而非 `ModuleNotFoundError`（更难诊断）。

**Why it happens:** pyarrow 使用 `importlib` 动态加载 C 扩展，PyInstaller 无法静态分析。

**How to avoid:** 使用 `collect_submodules('pyarrow')` 生成候选清单，然后从中筛选实际需要的子集加入 `windows_hidden`。[ASSUMED]

### Pitfall 3: torch CPU-only 未裁剪导致安装包体积失控

**What goes wrong:** `sentence-transformers` 依赖完整 `torch`，如果未指定 CPU-only 版本，安装包可能增加 1-3GB。

**Why it happens:** pip install 默认安装 CUDA 版 torch。

**How to avoid:** 在 Wave 0 安装时显式安装 CPU-only torch（`torch --index-url https://download.pytorch.org/whl/cpu`），然后验证 sentence-transformers 可正常使用。[ASSUMED]

### Pitfall 4: TRANSFORMERS_CACHE 优先级低于已存在的系统环境变量

**What goes wrong:** 用户系统中已设置 `TRANSFORMERS_CACHE`，Electron 注入的值被系统值覆盖（如果使用 `Object.assign` 而非字面量覆盖顺序）。

**Why it happens:** JavaScript `{ ...process.env, KEY: value }` 的 spread 顺序决定后者覆盖前者。

**How to avoid:** 确保 `backendChildEnv()` 中显式键值在 spread 之后（已在现有代码中正确实现，`...process.env` 在前，显式键在后）。[VERIFIED: codebase — electron/main.ts backendChildEnv()]

### Pitfall 5: lancedb Rust 扩展 (.pyd) 未被收集

**What goes wrong:** lancedb 的核心是一个 Rust 编译的 Python 扩展 (`lancedb._lib` 或类似)，PyInstaller 需要明确收集 `.pyd` 文件和关联的 `.dll`。

**How to avoid:** 运行 `pyinstaller --debug=imports --log-level DEBUG` 后检查是否出现 lancedb 相关的 `.pyd` 未被收集的警告。[ASSUMED]

## Runtime State Inventory

> This is a packaging phase (not rename/refactor), but model files constitute new runtime-deployed state.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | LanceDB 数据在 `CTRX_DATA_DIR/kb/`（已由 Phase 20 建立）| 无迁移；向量数据随 userData 保留 |
| Live service config | Electron extraResources 配置变更影响已安装版本 | 需重新安装（非热更新），可通过 NSIS 安装包覆盖安装 |
| OS-registered state | None — verified by scope | 无 |
| Secrets/env vars | `SENTENCE_TRANSFORMERS_HOME`/`TRANSFORMERS_CACHE`/`CTRX_MODELS_DIR` 新增注入 | Electron 主进程注入（D-09），后端无需改动 |
| Build artifacts | `electron/resources/models/bge-m3/` 约 2.5GB，未追踪入 git | 需 `.gitignore` 排除模型权重目录；文档记录人工下载步骤 |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini 已存在) |
| Config file | `backend/pytest.ini` |
| Quick run command | `pytest backend/tests/test_kb_service.py -q -x` |
| Full suite command | `pytest backend/tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-PKG-01 | hiddenimports 扩充后打包无 ModuleNotFoundError | build smoke | `pyinstaller ctrx_backend.spec --noconfirm --clean --log-level WARN` | ❌ Wave 0 — spec 变更后手动验证 |
| KB-PKG-01 | hiddenimports 变更同步 changelog（CI 门禁） | CI gate | `python scripts/check_hiddenimports_diff.py --base origin/master --spec ctrx_backend.spec --changelog docs/packaging/hiddenimports-changelog.md` | ✅ 脚本已存在 |
| KB-PKG-02 | Electron 注入 CTRX_MODELS_DIR / SENTENCE_TRANSFORMERS_HOME / TRANSFORMERS_CACHE | unit | `npx jest electron/tests/` (if exists) or manual | ❌ 需手动验证或新建测试 |
| KB-PKG-03 | 打包全链路烟测通过 | manual smoke (gated) | 手动执行 `docs/smoke-test-23.md` | ❌ Wave 1 新建文档 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_kb_service.py -q -x`
- **Per wave merge:** `pytest backend/tests -q`
- **Phase gate:** 手动烟测清单全部通过 + `check_hiddenimports_diff.py` 门禁通过，方可执行 `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `electron/resources/models/bge-m3/` — bge-m3 权重目录（需人工下载，约 2.5GB）
- [ ] `docs/smoke-test-23.md` — Phase 23 全链路烟测清单
- [ ] `.venv` 依赖安装：`pip install lancedb>=0.33.0 sentence-transformers>=5.5.1`

## Key Technical Facts (Verified from Codebase)

### 1. `check_hiddenimports_diff.py` 行为

[VERIFIED: codebase]
- `--base`: git ref（CI 使用 `origin/master`）
- `--spec`: spec 文件路径（`ctrx_backend.spec`）
- `--changelog`: changelog 文件路径（`docs/packaging/hiddenimports-changelog.md`）
- 逻辑：`spec中hiddenimports_token发生变化 AND changelog未变化 → exit 1`
- **Changelog 文件已存在**，内容为 Phase 12 基线（2026-05-28 条目）
- Phase 23 需在同一 commit 追加新条目

### 2. `kb_service.py` 模型加载逻辑

[VERIFIED: codebase]
```python
models_dir_raw = os.environ.get("CTRX_MODELS_DIR", "").strip()
if models_dir_raw:
    model_path = Path(models_dir_raw) / "bge-m3"
    model = SentenceTransformer(str(model_path), local_files_only=True)
```
- 变量名：`CTRX_MODELS_DIR`（不是 `SENTENCE_TRANSFORMERS_HOME`）
- 模型子目录：固定为 `"bge-m3"`
- 加载模式：`local_files_only=True`（完全离线，不尝试网络）

### 3. `electron/main.ts` `backendChildEnv()` 注入点

[VERIFIED: codebase]
```typescript
function backendChildEnv(port: number): NodeJS.ProcessEnv {
  const settings = loadSettings()
  const ragTopK = Number.isInteger(settings.ragTopK) ? settings.ragTopK : 3
  return {
    ...process.env,
    CTRX_PORT: String(port),
    CTRX_DATA_DIR: app.getPath('userData'),
    // ... other settings
    RAG_TOP_K: String(ragTopK),
    // Phase 23: add CTRX_MODELS_DIR, SENTENCE_TRANSFORMERS_HOME, TRANSFORMERS_CACHE here
  }
}
```
- `backendChildEnv()` 被 `spawnBackend()` 调用，`spawnBackend()` 被 `scheduleRestart()` 和 `bootstrap()` 调用 → 满足 D-10（每次 spawn/restart 均注入）
- `resourcesDir` 推导逻辑位于 `backendEntrypoint()` — 需提取为共享函数或复制逻辑到 `backendChildEnv`

### 4. `package.json` extraResources 格式

[VERIFIED: codebase]
- 使用 `from`/`to`/`filter` 对象格式（非 glob 字符串）
- 现有 `from: "electron/resources"` → `to: "electron/resources"` 条目，filter 含 `ctrx-backend-*/**`
- 扩展方式：在 filter 追加 `"models/**"` 或新增独立条目（planner 可选）

### 5. 现有文件状态

[VERIFIED: codebase filesystem scan]
- `electron/resources/models/` — **不存在**（需 Wave 0 创建）
- `electron/resources/ctrx-backend-win-x64-v1.2.0/` — 存在（v1.2 打包产物）
- `docs/packaging/hiddenimports-changelog.md` — **存在**（Phase 12 基线）
- `docs/packaging/smoke-checklist-template.md` — 存在（Phase 12 模板）
- `docs/smoke-test-23.md` — **不存在**（需 Wave 1 创建）
- `docs/packaging/` 目录已存在

### 6. .venv 包安装状态

[VERIFIED: codebase — pip list]
- `lancedb` — 未安装（requirements.txt 有声明）
- `pyarrow` — 未安装
- `sentence-transformers` — 未安装
- `torch` — 未安装
- 现有包：uvicorn, fastapi, sqlalchemy, pydantic-settings, httpx, anyio 等（全部已就位）

### 7. RAG 日志关键字（烟测 D-14 验证依据）

[CITED: 23-CONTEXT.md D-14/D-15]
- 烟测通过标准第 4 项：后端日志包含 `RAG context` 或 `few-shot` 关键字
- 验证方式：查看 `app.getPath('userData')/logs/backend.log`（Electron backendLogPath()）[VERIFIED: codebase]

## Open Questions

1. **bge-m3 模型目录格式**
   - What we know: `SentenceTransformer(path, local_files_only=True)` 从本地路径加载
   - What's unclear: 模型目录需要哪些具体文件（`config.json`? `model.safetensors`? 还是 HuggingFace hub snapshot 格式?）
   - Recommendation: Wave 0 执行 `model.save('electron/resources/models/bge-m3')` 后验证目录结构，确保 `SentenceTransformer(path, local_files_only=True)` 可重新加载

2. **torch CPU-only 安装包体积**
   - What we know: torch 完整版约 2-3GB；模型权重约 2.5GB
   - What's unclear: 安装包总体积是否可接受；是否需要 CPU-only 裁剪
   - Recommendation: Wave 0 使用 CPU-only torch 安装，记录最终安装包体积

3. **hiddenimports 实际最小集**
   - What we know: lancedb/pyarrow/sentence-transformers/torch 均需纳入，但确切子模块列表待测
   - Recommendation: Wave 0 安装后运行 `pyinstaller --debug=imports` 获取实际缺口列表

4. **electron/resources/models 是否加入 .gitignore**
   - What we know: bge-m3 约 2.5GB，不应提交到 git
   - Recommendation: 在 Wave 0 向 `.gitignore` 追加 `electron/resources/models/`，并在 build 文档中记录下载步骤

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | PyInstaller 打包 | ✓ [ASSUMED] | 3.11.x | — |
| PyInstaller | KB-PKG-01 | ✓ [ASSUMED] | 6.x | pip install pyinstaller |
| pip (venv) | 依赖安装 | ✓ | 24.0 [VERIFIED: pip list] | — |
| lancedb | KB-PKG-01 | ✗ | — | 必须安装（Wave 0 阻塞） |
| pyarrow | KB-PKG-01 | ✗ | — | lancedb 自动安装 |
| sentence-transformers | KB-PKG-01/02 | ✗ | — | 必须安装（Wave 0 阻塞） |
| torch (CPU) | KB-PKG-01/02 | ✗ | — | sentence-transformers 依赖 |
| bge-m3 模型权重 | KB-PKG-02 | ✗ | — | 必须下载（Wave 0 阻塞，约 2.5GB） |
| electron-builder | KB-PKG-02 | ✓ [ASSUMED] | ^26.8.1 | — |
| Node.js / npm | build pipeline | ✓ [ASSUMED] | v22.x | — |
| Internet access | bge-m3 下载 | ✓ [ASSUMED] | — | 无（模型必须内置，D-07） |

**Missing dependencies with no fallback:**
- lancedb, sentence-transformers, bge-m3 模型权重 — 阻断 Wave 1 所有工作

**Missing dependencies with fallback:**
- None additional — pyarrow and torch install automatically as transitive dependencies

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | 本阶段无新增输入面 |
| V6 Cryptography | no | 本阶段无加密算法变更 |
| V14 Config | yes | 环境变量注入仅在 Electron 主进程 backendChildEnv() 中（D-09）；后端不自解析；系统值被显式覆盖（D-12） |

**Supply chain note:** bge-m3 模型权重来自 BAAI（北京智源研究院）HuggingFace Hub。建议记录模型版本 hash 用于可审计性。[ASSUMED]

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase — `ctrx_backend.spec`] — 现有 hiddenimports 结构（common/windows/linux 分段）
- [VERIFIED: codebase — `scripts/check_hiddenimports_diff.py`] — 门禁脚本完整逻辑
- [VERIFIED: codebase — `electron/main.ts` `backendChildEnv()`] — env 注入点
- [VERIFIED: codebase — `backend/app/services/kb_service.py`] — 模型加载逻辑、CTRX_MODELS_DIR 消费
- [VERIFIED: codebase — `backend/app/config.py`] — models_dir() 函数
- [VERIFIED: codebase — `package.json` build.extraResources] — from/to/filter 格式
- [VERIFIED: codebase — `.github/workflows/backend-packaging-gate.yml`] — CI 门禁 changelog 路径
- [VERIFIED: codebase — `docs/packaging/hiddenimports-changelog.md`] — 文件已存在，Phase 12 基线
- [VERIFIED: codebase — pip list] — lancedb/pyarrow/sentence-transformers 未安装确认
- [VERIFIED: codebase — filesystem scan] — `electron/resources/models/` 不存在

### Secondary (MEDIUM confidence)

- [CITED: 23-CONTEXT.md] — 所有锁定决策 D-01 至 D-16
- [CITED: REQUIREMENTS.md] — KB-PKG-01/02/03 需求定义
- [CITED: Phase 12 RESEARCH.md] — PyInstaller 打包先例与策略

### Tertiary (LOW confidence)

- [ASSUMED] — lancedb/pyarrow/sentence-transformers 具体 hiddenimports 子模块列表（需 Wave 0 安装后验证）
- [ASSUMED] — bge-m3 模型大小约 2.5GB（需实际下载确认）
- [ASSUMED] — torch CPU-only 可满足 sentence-transformers 需求

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | lancedb hiddenimports 需要 `lancedb.remote`, `lancedb.embeddings` 等子模块 | Standard Stack / Pattern 1 | 若 list 不完整 → clean VM 出现 ModuleNotFoundError（可在 Wave 1 打包测试中发现） |
| A2 | bge-m3 模型约 2.5GB | Critical Pre-conditions | 若更大 → 安装包体积超出用户预期；若更小 → 无负面影响 |
| A3 | `SentenceTransformer.save()` 输出的目录格式兼容 `SentenceTransformer(path, local_files_only=True)` 加载 | Pattern 1 / Pitfall 1 | 若格式不兼容 → 启动时 OSError（可在 Wave 0 验证） |
| A4 | torch CPU-only 足够运行 bge-m3 inference | Standard Stack | 若 bge-m3 依赖 CUDA → 需额外处理（可在 Wave 0 encode 测试中验证） |
| A5 | extraResources filter `"models/**"` 追加到现有条目即可正确打包 models 目录 | Pattern 3 | 若 electron-builder 的 from/to/filter 语义不支持 → 需独立条目（低风险） |
| A6 | 添加 `models/**` glob 到现有 extraResources filter 会包含 `electron/resources/models/bge-m3/` 所有文件 | Pattern 3 | 若路径不匹配 → 安装后 models 目录为空（可在测试安装后验证） |

## Metadata

**Confidence breakdown:**
- Critical facts (spec structure, Electron env injection, changelog path, venv state): HIGH — all verified from codebase
- hiddenimports exact module list: LOW — uninstalled packages; requires Wave 0 testing
- Model packaging details (size, directory format): LOW — no model downloaded yet
- Architecture patterns (extraResources extension, env injection): HIGH — verified from existing code

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable packaging domain; but hiddenimports list may change as lancedb evolves)
