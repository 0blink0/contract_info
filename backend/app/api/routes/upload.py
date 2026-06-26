from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.api.deps import verify_api_key
from backend.app.api.schemas import UploadResponse
from backend.app.services.upload_service import persist_upload, validate_filename

router = APIRouter(tags=["upload"], dependencies=[Depends(verify_api_key)])


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    try:
        validate_filename(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    try:
        file_id = persist_upload(content, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadResponse(
        job_id=file_id,
        status="pending",
        filename=Path(file.filename).name,
    )
