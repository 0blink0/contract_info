# Phase CTRX-12 Plan 01 Summary

## 完成情况

- 执行方式：严格按顺序完成 Task 1 -> Task 2 -> Task 3
- Git 提交：未执行（按要求不提交）

## 改动文件

- `desktop_main.py`
- `backend/tests/test_desktop_main.py`
- `ctrx_backend.spec`
- `scripts/check_hiddenimports_diff.py`
- `.github/workflows/backend-packaging-gate.yml`
- `docs/packaging/hiddenimports-changelog.md`
- `scripts/package_backend.ps1`
- `scripts/package_backend.sh`
- `electron/resources/.backend-manifest.json`

## 任务结果

### Task 1: desktop_main 单入口与 fail-fast

- 新增资源目录 fail-fast 断言：`alembic/`、`dicts/`、`templates/` 任一缺失立即抛错
- 保持启动链顺序：设置 sqlite `DATABASE_URL` -> 清理 `get_settings` 缓存 -> 迁移 -> 启动 uvicorn
- 测试新增并覆盖“不回退到 PostgreSQL”场景

### Task 2: 单 spec + hiddenimports 审计基线

- 新增 `ctrx_backend.spec`（单 spec，按 common/windows/linux 分段 hiddenimports）
- `datas` 显式包含 `alembic`、`dicts`、`templates`
- `excludes` 显式排除 `psycopg2`
- 新增 `scripts/check_hiddenimports_diff.py`，要求 hiddenimports 变更必须同步 changelog
- 新增 CI 门禁工作流 `backend-packaging-gate.yml`
- 新增 `docs/packaging/hiddenimports-changelog.md`

### Task 3: 产物落位与回滚锚点

- 新增 `scripts/package_backend.ps1`：Windows 打包、落位到 `electron/resources/ctrx-backend-<platform>-v<version>`、保留 current+previous
- 新增 `scripts/package_backend.sh`：Linux 同步落位逻辑
- 新增 `electron/resources/.backend-manifest.json` 并在脚本中更新 `current/previous`

## Verify 命令结果（最终）

1. `pytest backend/tests/test_desktop_main.py -q -x`
   - 结果：通过（`5 passed`）
2. `pyinstaller ctrx_backend.spec --noconfirm --clean --log-level WARN`
   - 结果：通过（构建成功；存在第三方依赖告警但不阻断）
3. `python scripts/check_hiddenimports_diff.py --base origin/master --spec ctrx_backend.spec --changelog docs/packaging/hiddenimports-changelog.md`
   - 结果：通过（`hiddenimports gate passed.`）
4. `powershell -ExecutionPolicy Bypass -File scripts/package_backend.ps1 -Platform win-x64 -Version 1.2.0`
   - 结果：通过（产物落位到 `electron/resources/ctrx-backend-win-x64-v1.2.0`）
5. `bash scripts/package_backend.sh --platform linux-x64 --version 1.2.0`
   - 结果：阻塞（当前 Windows 环境缺少可用 bash/WSL `/bin/bash`）

## 风险与后续建议

- 风险 1：Linux 打包验证仍受当前机器无 `bash` 环境限制，需在 WSL2/CI Linux runner 复验。
- 风险 2：hiddenimports 基线是宽覆盖首版，后续在 clean VM 仍可能暴露漏项。
- 建议 1：在 Linux 环境执行 `bash scripts/package_backend.sh --platform linux-x64 --version 1.2.0`。
- 建议 2：保留 `docs/packaging/hiddenimports-changelog.md` 的增量审计，减少后续 Phase 13 集成风险。
