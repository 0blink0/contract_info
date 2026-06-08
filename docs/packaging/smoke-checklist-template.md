# Phase 12 Smoke Checklist Template

Use this checklist in a clean environment before release.

## Execution Metadata

- Executor:
- Date (UTC):
- Machine / VM:
- OS:
- Build version:
- Backend binary path:
- `CTRX_DATA_DIR`:

## Preconditions

- [ ] Clean machine (no Python runtime dependency required for packaged backend)
- [ ] Backend package present (`ctrx-backend` directory with executable)
- [ ] Golden input docx prepared
- [ ] Data directory prepared and writable

## Smoke Chain (Windows clean VM)

- [ ] Start backend executable
- [ ] `GET /api/v1/health` returns `{"status":"ok"}`
- [ ] Upload succeeds (`POST /api/v1/upload`)
- [ ] Run pipeline succeeds (`POST /api/v1/jobs/{job_id}/run`)
- [ ] Job reaches `exported`
- [ ] Download succeeds (`GET /api/v1/jobs/{job_id}/download/product-elements`)
- [ ] Script exits with code `0` on PASS
- [ ] Script exits with non-zero on any FAIL (release gate)

## Data Isolation

- [ ] `CTRX_DATA_DIR/ctrx.db` exists after run
- [ ] Runtime files are created under `CTRX_DATA_DIR` only
- [ ] Install directory has no runtime `ctrx.db/uploads/exports` writes

## Linux Startup Evidence

- [ ] Linux packaged backend starts for `--help`
- [ ] Startup log contains no `ModuleNotFoundError`
- [ ] Startup log contains no `postgresql` / `psycopg2`

## Evidence Collected

- [ ] Commands used
- [ ] Logs paths
- [ ] Screenshots
- [ ] Download artifact hash
- [ ] Final verdict: PASS / FAIL
