---
status: partial
phase: 14-build-pipeline
source: [14-VERIFICATION.md]
started: 2026-05-29T06:30:00Z
updated: 2026-05-29T06:30:00Z
---

## Current Test

Human checkpoint approved during plan 14-03 execution (Task 2). Pending: Linux build on Ubuntu 22.04.

## Tests

### 1. Windows installer runtime acceptance

expected: Installer completes without Windows Defender quarantine; CTRX loading screen appears ("CTRX 正在启动后端，请稍候..."); app progresses to main interface; resources\electron\resources\ctrx-backend-win-x64-v1.2.0\ present in install directory
result: approved — user confirmed during plan 14-03 Task 2 checkpoint

### 2. Linux AppImage on Ubuntu 22.04

expected: bash scripts/build.sh --version 1.2.0 produces dist/CTRX-1.2.0-x64.AppImage; AppImage launches without glibc errors on Ubuntu 22.04 (glibc 2.35)
result: [pending — requires Ubuntu 22.04 machine]

### 3. Linux deb via dpkg

expected: dist/CTRX-1.2.0-x64.deb produced; sudo dpkg -i exits 0; app appears in system menu
result: [pending — requires Ubuntu 22.04 machine]

## Summary

total: 3
passed: 1
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
