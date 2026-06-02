import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.api.deps import verify_api_key
from backend.app.services.kb_service import get_kb_service

router = APIRouter(prefix="/kb", tags=["kb"], dependencies=[Depends(verify_api_key)])


class KbEntryInput(BaseModel):
    field_name: str
    field_value: str
    snippet: str = ""
    source_job_id: str = ""
    source_filename: str = ""


class KbEntriesRequest(BaseModel):
    entries: list[KbEntryInput] = Field(..., max_length=20)


class KbEntriesResponse(BaseModel):
    ids: list[str]
    count: int


class KbEntryItem(BaseModel):
    id: str
    field_name: str
    field_value: str
    snippet: str
    source_job_id: str
    source_filename: str
    created_at: str


class KbListResponse(BaseModel):
    items: list[KbEntryItem]
    total: int


@router.post("/entries", response_model=KbEntriesResponse)
async def post_kb_entries(body: KbEntriesRequest) -> KbEntriesResponse:
    svc = get_kb_service()
    if svc is None or not svc.model_available:
        raise HTTPException(status_code=503, detail="知识库功能不可用（bge-m3 模型未加载）")
    ids = await svc.add_entries([item.model_dump() for item in body.entries])
    return KbEntriesResponse(ids=ids, count=len(ids))


@router.get("/entries", response_model=KbListResponse)
def get_kb_entries(
    field_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> KbListResponse:
    svc = get_kb_service()
    if svc is None:
        return KbListResponse(items=[], total=0)
    result = svc.list_entries(field_name=field_name, page=page, page_size=page_size)
    items = result.get("items", [])
    total = result.get("total", 0)
    return KbListResponse(items=[KbEntryItem(**item) for item in items], total=total)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb_entry(entry_id: str) -> None:
    try:
        uuid.UUID(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="entry_id 格式无效") from exc

    svc = get_kb_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="知识库不可用")
    svc.delete_entry(entry_id)
