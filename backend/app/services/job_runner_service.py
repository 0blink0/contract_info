"""Bounded thread pool for parallel contract pipeline jobs."""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from backend.app.services.pipeline_service import run_pipeline

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctrx-pipeline")


class JobRunner:
    def submit(self, file_id: uuid.UUID) -> None:
        _executor.submit(_run_in_worker, file_id)


def _run_in_worker(file_id: uuid.UUID) -> None:
    try:
        run_pipeline(file_id)
    except Exception:
        logger.exception("pipeline failed for job %s", file_id)


_runner = JobRunner()


def get_runner() -> JobRunner:
    return _runner


def shutdown_runner(wait: bool = False) -> None:
    _executor.shutdown(wait=wait, cancel_futures=not wait)
