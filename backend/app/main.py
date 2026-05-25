from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import health, jobs, upload
from backend.app.config import cors_origin_list

app = FastAPI(
    title="CTRX Contract Extraction API",
    description="上传 docx → 解析 → 抽取 → 导出 Excel",
    version="0.1.0",
)

origins = cors_origin_list()
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

v1 = APIRouter(prefix="/api/v1")
v1.include_router(health.router)
v1.include_router(upload.router)
v1.include_router(jobs.router)
app.include_router(v1)
