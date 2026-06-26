import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import health, jobs, kb, merge, upload
from backend.app.config import cors_origin_list
from backend.app.services.job_runner_service import get_runner, shutdown_runner
from backend.app.services.kb_service import init_kb_service


_INTERRUPTED_STATUS_MAP = {
    "parsing": "failed",
    "extracting": "extraction_failed",
    "exporting": "export_failed",
}


def _reset_and_resume_jobs() -> None:
    """On startup: reset in-flight jobs from a previous crash, then resume queued ones."""
    from backend.app.db.session import SessionLocal
    from backend.app.models.contract_file import ContractFile
    from backend.app.services.pipeline_service import count_in_progress, get_next_queued_id
    from sqlalchemy import select

    session = SessionLocal()
    try:
        stmt = select(ContractFile).where(ContractFile.status.in_(list(_INTERRUPTED_STATUS_MAP)))
        rows = list(session.scalars(stmt))
        for row in rows:
            row.status = _INTERRUPTED_STATUS_MAP[row.status]
            row.error_message = "backend restarted while job was in progress"
        if rows:
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    runner = get_runner()
    while count_in_progress() < 3:
        next_id = get_next_queued_id()
        if next_id is None:
            break
        runner.submit(next_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, init_kb_service)
    loop.run_in_executor(None, _reset_and_resume_jobs)
    yield
    shutdown_runner(wait=False)


app = FastAPI(
    title="CTRX Contract Extraction API",
    description="上传 docx → 解析 → 抽取 → 导出 Excel",
    version="2.0.0",
    lifespan=lifespan,
)

origins = cors_origin_list()
desktop_mode = bool(os.environ.get("CTRX_DATA_DIR"))
if origins or desktop_mode:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://127\.0\.0\.1(:\d+)?" if desktop_mode else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

v1 = APIRouter(prefix="/api/v1")
v1.include_router(health.router)
v1.include_router(upload.router)
v1.include_router(jobs.router)
v1.include_router(kb.router)
v1.include_router(merge.router)
app.include_router(v1)
