# Phase 12 Smoke Evidence

This document stores auditable smoke-test evidence for Phase 12 packaging acceptance.

## Run Metadata

- Executor:
- Date (UTC):
- Machine / VM:
- OS:
- Build version:
- Backend path:
- `CTRX_DATA_DIR`:

## Windows Clean VM Main-Chain Evidence

### Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_phase12.ps1 `
  -BackendExePath "electron/resources/ctrx-backend-win-x64-v1.2.0/ctrx-backend.exe" `
  -DataDir "$env:TEMP\ctrx-smoke" `
  -GoldenDocx "example/_golden_contract.docx"
```

### 日志 / Logs

- Backend stdout/stderr log:
- Script output:

### 截图 / Screenshots

- Health passed:
- Upload returned job id:
- Job reached exported:
- Download file exists:
- Isolation check passed:

### Download Artifact Hash

- File:
- SHA256 hash:

### Result

- Verdict: PASS / FAIL
- Notes:

## Linux Clean Startup Evidence

### Command

```bash
CTRX_DATA_DIR=/tmp/ctrx-smoke-linux \
  "electron/resources/ctrx-backend-linux-x64-v1.2.0/ctrx-backend" --help \
  > /tmp/ctrx-linux-start.log 2>&1 || true
! rg "ModuleNotFoundError|postgresql|psycopg2" /tmp/ctrx-linux-start.log
```

### Log Assertion

- Log file: `/tmp/ctrx-linux-start.log`
- Contains forbidden keywords (`ModuleNotFoundError|postgresql|psycopg2`): YES / NO
- Verdict: PASS / FAIL

## Release Gate Decision

- Smoke gate status: PASS / FAIL
- Release blocked: YES / NO
- Block reason (if any):
