from fastapi import APIRouter
from pydantic import BaseModel

from app.service.similar_service import SimilarService

router = APIRouter(prefix="/api")

class SimilarRequest(BaseModel):
    summary: dict
    user_id: str

@router.post("/similar")
async def find_similar(req: SimilarRequest):
    return SimilarService.find_similar(req.summary, req.user_id)
