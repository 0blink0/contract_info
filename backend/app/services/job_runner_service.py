"""Bounded thread pool for parallel contract pipeline jobs."""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from backend.app.services.pipeline_service import run_pipeline

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctrx-pipeline")
_promote_lock = threading.Lock()


class JobRunner:
    def submit(self, file_id: uuid.UUID) -> None:
        _executor.submit(_run_in_worker, file_id)


def _promote_next_queued() -> None:
    """After a job finishes, promote the oldest queued job into the thread pool."""
    with _promote_lock:
        from backend.app.services.pipeline_service import count_in_progress, get_next_queued_id
        if count_in_progress() >= 3:
            return
        next_id = get_next_queued_id()
        if next_id is not None:
            logger.info("auto-promoting queued job %s", next_id)
            _executor.submit(_run_in_worker, next_id)


def _run_in_worker(file_id: uuid.UUID) -> None:
    try:
        run_pipeline(file_id)
    except Exception:
        logger.exception("pipeline failed for job %s", file_id)
    finally:
        _promote_next_queued()


_runner = JobRunner()


def get_runner() -> JobRunner:
    return _runner


def shutdown_runner(wait: bool = False) -> None:
    _executor.shutdown(wait=wait, cancel_futures=not wait)
