# Phase 12 Plan 02 Summary

## Execution Status

- Plan: `CTRX-12-pyinstaller/12-02-PLAN.md`
- Resume mode: rerun after interrupted execution
- Commit policy for this run: no git commit (explicitly required)
- Overall status: done (Linux verify deferred by user decision)

## Completed Scope

### Task 1: Windows clean VM main-chain smoke script and release gate

Implemented:
- `scripts/smoke_phase12.ps1`
  - Starts packaged backend with `CTRX_DATA_DIR` and `CTRX_PORT`
  - Executes chain check: `health -> upload -> run pipeline -> download`
  - Polls job status until `exported`, fails on timeout or failed state
  - Verifies data isolation (`ctrx.db` must exist under `CTRX_DATA_DIR`)
  - Detects install-dir runtime writes (`ctrx.db/uploads/exports`) and fails
  - Enforces release gate via non-zero exit on any failure

Documentation artifacts:
- `docs/packaging/smoke-checklist-template.md`
- `docs/packaging/phase12-smoke-evidence.md`

### Task 2: Linux clean startup evidence section

Updated:
- `docs/packaging/phase12-smoke-evidence.md`
  - Added Linux startup check command and log assertion section
  - Added explicit forbidden-keyword assertion for:
    - `ModuleNotFoundError`
    - `postgresql`
    - `psycopg2`

## Verification Results

### Verify 1: Windows smoke chain script

Command:
- `powershell -ExecutionPolicy Bypass -File scripts/smoke_phase12.ps1 -BackendExePath "electron/resources/ctrx-backend-win-x64-v1.2.0/ctrx-backend.exe" -DataDir "$env:TEMP\ctrx-smoke" -GoldenDocx "example/_golden_contract.docx"`

Result:
- PASS (exit code 0)
- Notes:
  - 主链路 `health -> upload -> run -> download` 通过
  - `CTRX_DATA_DIR` 隔离校验通过
  - 使用仓库现有样本 `../_merge_backup_pre_master/技术设计文档.docx` 执行

### Verify 2: Linux clean startup check

Command:
- `bash -lc 'CTRX_DATA_DIR=/tmp/ctrx-smoke-linux "electron/resources/ctrx-backend-linux-x64-v1.2.0/ctrx-backend" --help > /tmp/ctrx-linux-start.log 2>&1 || true; ! rg "ModuleNotFoundError|postgresql|psycopg2" /tmp/ctrx-linux-start.log'`

Result:
- SKIPPED (user-approved temporary defer)
- Note:
  - Linux clean startup verify is explicitly deferred for later environment window.

### Verify 3: Evidence template keyword check

Command intent:
- Ensure evidence template contains `PASS|FAIL|截图|日志|hash`

Result:
- PASS (content check matched these keywords in evidence document)

## Deferred Items

1. 默认样本路径 `example/_golden_contract.docx` 在仓库中不存在（需补齐或在脚本中改为可配置默认值）。
2. Linux clean 启动验证已按用户决定暂时跳过，不阻塞后续阶段。

## Suggested Next Actions

1. 补充或指定标准黄金样本路径（建议恢复 `example/_golden_contract.docx`）。
2. 在 Linux 主机或可用 WSL 环境补跑 Linux verify，并将证据回填到本文档。
