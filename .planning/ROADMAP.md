# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5（shipped 2026-05-26）→ [archive](milestones/1.0-ROADMAP.md)
- ✅ **v1.1 抽取质量与导出扩展** — Phases 6–10（shipped 2026-05-26）→ [archive](milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 桌面化交付** — Phases 11–14（in progress）

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-05-26</summary>

- [x] **Phase 1: 文档解析** - docx → Document JSON + PostgreSQL schema + CLI parse
- [x] **Phase 2: 字段抽取** - 规则 + 章节窗 LLM 抽取、字典校验、extract CLI
- [x] **Phase 3: Excel 导出** - 产品要素与运营费率 xlsx 填充、export CLI
- [x] **Phase 4: API 层** - upload / run / poll / download FastAPI 端点
- [x] **Phase 5: 前端界面** - Element Plus 上传、任务列表、步骤条、双下载

</details>

<details>
<summary>✅ v1.1 抽取质量与导出扩展 (Phases 6–10) — SHIPPED 2026-05-26</summary>

- [x] **Phase 6: 黄金回归** - 黄金样例基线、回归脚本、P1+ 字段扩展
- [x] **Phase 7: 申赎费率第五表** - 第五张导入表导出逻辑与模板对齐
- [x] **Phase 8: 路径 B JSON** - 业绩报酬/开放日结构化草稿与 CRM 输出
- [x] **Phase 9: LLM 校验层** - 校验 API、ValidationPanel 前端展示
- [x] **Phase 10: UI 导航与下载** - 左侧菜单路由、五表下载、前端收口

</details>

### 🚧 v1.2 桌面化交付

**Milestone Goal:** 将 CTRX 从 Docker-only 部署转型为 Electron 桌面应用，双击安装包即用，内嵌 Python + SQLite，首次启动完成 LLM 配置。

- [x] **Phase 11: SQLite 迁移与路径修复** - 替换 PostgreSQL 方言类型，修复 _MEIPASS 路径假设，开启 WAL，程序化 Alembic (completed 2026-05-28)
  - **Wave 0:** 11-01 (RED 测试基础设施)
  - **Wave 1 *(blocked on Wave 0)*:** 11-02 (DB-01 类型替换), 11-03 (DB-02 路径解析) — 并行
  - **Wave 2 *(blocked on Wave 1)*:** 11-04 (DB-03 WAL + DB-04 desktop_main)
  - **Cross-cutting:** 11-01 测试文件被 Wave 1–2 所有 verify 命令依赖；`data_dir()` (11-03) 被 desktop_main.py (11-04) 导入
- [ ] **Phase 12: PyInstaller 打包** - desktop_main.py 入口，完整 spec，干净 VM 烟雾测试通过
- [ ] **Phase 13: Electron 壳与 IPC** - 子进程生命周期、contextBridge IPC、首次启动向导、Settings 页面
- [x] **Phase 14: 构建流水线** - electron-builder NSIS + AppImage + deb，4 步构建脚本 (completed 2026-05-29)

## Phase Details

### Phase 11: SQLite 迁移与路径修复
**Goal**: 后端以纯 SQLite 运行，所有 PostgreSQL 方言依赖清除，路径解析在 PyInstaller _MEIPASS 和开发模式下均正确
**Depends on**: Phase 10 (v1.1 shipped codebase)
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
  1. `alembic upgrade head` 在 SQLite URL 下执行无错误，7 个迁移全部通过（不依赖 PostgreSQL）
  2. 设置 `CTRX_DATA_DIR=/tmp/test` 后，uploads/ 和 exports/ 正确写入该目录，不依赖 `__file__` 相对路径
  3. Uvicorn 多线程并发上传 3 个合同，无 SQLite 锁超时（WAL 模式已开启）
  4. `desktop_main.py` 冷启动时自动执行 Alembic 迁移，首次运行建表，再次运行幂等无错误
  5. 单元测试：`extraction_result` 列序列化/反序列化返回 dict 而非 str
**Plans:** 4/4 plans complete
Plans:
- [x] 11-01-PLAN.md — Wave 0 test infrastructure (RED): 4 test files, 10 test cases covering DB-01..DB-04
- [x] 11-02-PLAN.md — DB-01 type replacement: ORM model + migrations 001/002/006/007 (Wave 1)
- [x] 11-03-PLAN.md — DB-02 path resolution: config.py helpers + 6 consumer files (Wave 1, parallel)
- [x] 11-04-PLAN.md — DB-03 WAL mode (session.py) + DB-04 desktop_main.py + alembic/env.py (Wave 2)

### Phase 12: PyInstaller 打包
**Goal**: Python/FastAPI 后端打包为可独立运行的 --onedir 二进制，无 Python 环境机器可完整跑通上传-抽取-下载流程
**Depends on**: Phase 11
**Requirements**: PKG-01, PKG-02, PKG-03
**Success Criteria** (what must be TRUE):
  1. `ctrx-backend.exe`（Windows）和 `ctrx-backend`（Linux）在无 Python 安装的干净 VM 上启动不报 ModuleNotFoundError
  2. 干净 Windows VM 烟雾测试：上传合同 → 抽取 → 下载 xlsx 全部可用，`CTRX_DATA_DIR` 正确隔离数据
  3. 二进制产物已放入 `electron/resources/`，electron-builder 可通过 `extraResources` 引用
  4. `lru_cache` 清除机制生效：打包二进制不尝试连接 PostgreSQL
**Plans:** 2/2 plans ready
Plans:
- [x] 12-01-PLAN.md — 打包基础：desktop_main 入口加固、单 spec（含 hiddenimports CI gate）、资源落位与 manifest 回滚锚点
- [x] 12-02-PLAN.md — 验收闭环：Windows clean VM 主链路烟测 + Linux clean 启动证据 + 失败阻断（Linux 验证按用户决定暂时跳过）

### Phase 13: Electron 壳与 IPC
**Goal**: 用户双击 `electron .` 启动桌面应用，Python 子进程自动管理，首次启动显示 LLM 配置向导，可通过 Settings 页面随时修改配置
**Depends on**: Phase 12
**Requirements**: ELEC-01, ELEC-02, ELEC-03, ELEC-04
**Success Criteria** (what must be TRUE):
  1. 应用启动时显示加载隔屏，`/api/v1/health` 返回 200 后自动进入主界面（冷启动不显示空白页或网络错误）
  2. Python 子进程崩溃时应用自动重试最多 3 次，3 次失败后显示含日志路径的错误对话框
  3. 首次启动（或 llmBaseUrl/llmApiKey 为空）强制显示 3 步向导，向导完成前无法进入主界面
  4. Settings 页面保存新 API Key 后 Python 子进程重启，新配置立即生效（LLM 请求使用新 Key）
  5. `userData/config.json` 正确存储 llmBaseUrl、llmApiKey、llmModel，应用重启后配置持久
**Plans:** 2/2 plans ready
Plans:
- [x] 13-01-PLAN.md — 主进程与 IPC 基线：生命周期状态机、三通道窄桥、配置存储校验（ELEC-01/02）
- [x] 13-02-PLAN.md — 体验层闭环：首启向导强门禁 + Settings 保存后重启回滚（ELEC-03/04）
**UI hint**: yes

### Phase 14: 构建流水线
**Goal**: 一条命令产出可分发的 Windows NSIS 安装包（.exe）、Linux AppImage 和 .deb，构建步骤有文档脚本
**Depends on**: Phase 13
**Requirements**: BUILD-01, BUILD-02, BUILD-03
**Success Criteria** (what must be TRUE):
  1. `CTRX-Setup-1.2.0.exe` 在干净 Windows 11 VM 上安装并运行，Windows Defender 不隔离（--onedir 模式）
  2. `CTRX-1.2.0.AppImage` 在 Ubuntu 22.04 上运行，应用完整可用
  3. `CTRX-1.2.0.deb` 通过 `dpkg -i` 安装，应用可从系统菜单启动
  4. `.ps1` 和 `.sh` 构建脚本各一份，4 步流程（PyInstaller → Vite → tsc → electron-builder）可无人值守运行
**Plans:** 3/3 plans complete
Plans:
  - **Wave 0:**
- [x] 14-01-PLAN.md — root package.json (electron-builder inline config) + tsconfig.electron.json + npm install + icon placeholders (BUILD-01, BUILD-03)
  - **Wave 1 *(blocked on Wave 0)*:**
- [x] 14-02-PLAN.md — scripts/build.ps1 + scripts/build.sh 4-step dispatchers with fail-fast + --extraMetadata version injection (BUILD-02)
  - **Wave 2 *(blocked on Wave 1)*:**
- [x] 14-03-PLAN.md — tsc dry-run + Windows build smoke test + human acceptance gate (BUILD-01, BUILD-02, BUILD-03)
**Cross-cutting constraints:** `extraResources.to="electron/resources"` must match main.ts backendEntrypoint() candidate 3; `preload.cjs` staged as FileSet at `dist/electron/preload.cjs`; version injected via `--extraMetadata` (never modifies package.json source)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. 文档解析 | v1.0 | — | Complete | 2026-05-26 |
| 2. 字段抽取 | v1.0 | — | Complete | 2026-05-26 |
| 3. Excel 导出 | v1.0 | — | Complete | 2026-05-26 |
| 4. API 层 | v1.0 | — | Complete | 2026-05-26 |
| 5. 前端界面 | v1.0 | — | Complete | 2026-05-26 |
| 6. 黄金回归 | v1.1 | — | Complete | 2026-05-26 |
| 7. 申赎费率第五表 | v1.1 | — | Complete | 2026-05-26 |
| 8. 路径 B JSON | v1.1 | — | Complete | 2026-05-26 |
| 9. LLM 校验层 | v1.1 | — | Complete | 2026-05-26 |
| 10. UI 导航与下载 | v1.1 | — | Complete | 2026-05-26 |
| 11. SQLite 迁移与路径修复 | v1.2 | 4/4 | Complete   | 2026-05-28 |
| 12. PyInstaller 打包 | v1.2 | 2/2 | Complete | 2026-05-29 |
| 13. Electron 壳与 IPC | v1.2 | 2/2 | Complete | 2026-05-29 |
| 14. 构建流水线 | v1.2 | 3/3 | Complete   | 2026-05-29 |

---
*Roadmap updated: 2026-05-29 — Phase 14 planned (3 plans, 3 waves)*
