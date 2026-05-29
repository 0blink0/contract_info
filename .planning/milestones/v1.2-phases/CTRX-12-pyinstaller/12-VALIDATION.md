---
phase: 12
slug: CTRX-12-pyinstaller
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-28
updated: 2026-05-28
---

# Phase 12 验证策略

**阶段：** PyInstaller 打包  
**日期：** 2026-05-28

## 需求到验证映射（Nyquist 8a/8b）

| 需求 | 关键行为 | 自动化命令 | 类型 | 归属计划 |
|------|----------|------------|------|----------|
| PKG-01 | `desktop_main.py` 单入口启动链（env 注入、cache_clear、程序化迁移、禁用 PostgreSQL 回退） | `pytest backend/tests/test_desktop_main.py -q -x` | unit/integration | 12-01 Task 1 |
| PKG-02 | `ctrx_backend.spec` 能稳定产出 onedir，hiddenimports/datas/excludes 完整，`psycopg2` 被排除 | `pyinstaller ctrx_backend.spec --noconfirm --clean --log-level WARN` | build smoke | 12-01 Task 2 |
| PKG-02 (D-08) | hiddenimports 变更必须同步 changelog，否则 CI 阻断 | `python scripts/check_hiddenimports_diff.py --base origin/master --spec ctrx_backend.spec --changelog docs/packaging/hiddenimports-changelog.md` | policy gate | 12-01 Task 2 |
| PKG-02 (落位) | 产物进入 `electron/resources/` 且维护 current/previous manifest | `powershell -ExecutionPolicy Bypass -File scripts/package_backend.ps1 -Platform win-x64 -Version 1.2.0` | packaging | 12-01 Task 3 |
| PKG-03 | clean VM 主链路烟测（上传->抽取->下载）与证据输出 | `powershell -ExecutionPolicy Bypass -File scripts/smoke_phase12.ps1 -BackendExePath "<path>" -DataDir "$env:TEMP\ctrx-smoke" -GoldenDocx "example/_golden_contract.docx"` | UAT smoke | 12-02 Task 1 |
| Success Criteria #1 (Linux) | Linux clean 启动无 `ModuleNotFoundError` | `bash -lc 'CTRX_DATA_DIR=/tmp/ctrx-smoke-linux "electron/resources/ctrx-backend-linux-x64-v1.2.0/ctrx-backend" --help > /tmp/ctrx-linux-start.log 2>&1 || true; ! rg "ModuleNotFoundError|postgresql|psycopg2" /tmp/ctrx-linux-start.log'` | startup smoke | 12-02 Task 2 |

## Wave 0 缺口与补齐顺序（Nyquist 8c）

1. 先落地 `ctrx_backend.spec` 与 `scripts/check_hiddenimports_diff.py`，保证 PKG-02 的构建与门禁可跑。
2. 再落地 `scripts/package_backend.ps1/.sh` 与 `.backend-manifest.json`，建立资源落位与回滚锚点。
3. 最后在 12-02 落地 `scripts/smoke_phase12.ps1`，输出结构化证据并执行发布阻断。

## 连续采样策略（Nyquist 8d）

- 在 12-01 的 4 个实现任务中，至少 3 个任务包含可执行自动化命令（Task 1/2/3/4 全覆盖）。
- 每次 hiddenimports 变更必须触发 policy gate 与 build smoke 两条命令。
- 阶段收口前必须至少完成 1 次 clean VM 真实烟测，并保留 checklist+日志+截图。

## 阶段 UAT（人工 + 自动混合）

1. 在无 Python 的 Windows VM 启动 `ctrx-backend.exe`，确认无 `ModuleNotFoundError`。
2. 调 `GET /api/v1/health` 返回 200。
3. 上传固定黄金合同，执行抽取直到 `done`。
4. 下载 xlsx，确认文件可打开且落在 `CTRX_DATA_DIR` 指定目录。
5. 失败任一步即阻断发布，并在 `evidence/phase12/` 留存证据。
