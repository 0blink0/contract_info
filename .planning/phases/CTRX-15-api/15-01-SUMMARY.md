# Phase 15 Plan 01 Summary

**JobRunner + 全局 3 槽并行守门**

## Delivered

- `job_runner_service.py` — `ThreadPoolExecutor(max_workers=3)`, `submit`, `shutdown_runner`
- `pipeline_service.count_in_progress()` — 仅 `IN_PROGRESS` 状态计数
- `run_job` — 全局 ≥3 返回 409（结构化 detail）；改用 `get_runner().submit`
- `main.py` — lifespan 关闭线程池
- `test_parallel_run.py` — 409、3×submit、max_workers 测试

## Requirements

- UP-04 ✓
- API-03 ✓
