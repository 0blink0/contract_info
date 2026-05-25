# Phase 5 Discussion Log

**Date:** 2026-05-25

Canonical decisions: `05-CONTEXT.md`

## Choices

| Topic | Chosen | Not chosen |
|-------|--------|------------|
| Stack | Vue 3 + Vite + TS | Plain HTML, Vue JS-only |
| Flow | Upload then manual「开始处理」 | Auto-run on upload |
| Status UI | 3-step stepper | Badge-only |
| Warnings | Expandable list (+ API extend) | Count only / hidden |
| Download | Two API buttons | Client zip / backend zip |
| API Key | Dev no UI; prod `VITE_API_KEY` | localStorage config page |
| Deploy | Vite proxy `/api` | CORS-only direct to :8000 |
| Failure | Retry via POST /run | Re-upload only |
| Scope | History list + `GET /jobs` | Single-job-only page |

## Scope note

History list requires a small backend addition (`GET /api/v1/jobs`) documented in CONTEXT D-13.
