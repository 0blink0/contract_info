import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import health, jobs, upload
from backend.app.config import cors_origin_list
from backend.app.services.job_runner_service import shutdown_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    shutdown_runner(wait=False)


app = FastAPI(
    title="CTRX Contract Extraction API",
    description="上传 docx → 解析 → 抽取 → 导出 Excel",
    version="0.1.0",
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
app.include_router(v1)
