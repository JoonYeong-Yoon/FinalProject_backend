from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from app.service.chat_service import ChatService

router = APIRouter(prefix="/api")
chat_service = ChatService()

# 8가지 캐릭터 타입 정의 (5가지 신규 + 3가지 레거시)
CharacterType = Literal[
    # 새로운 5가지 전문 캐릭터
    "default",      # 헬스 코치 지니
    "trainer",      # 근육맨 트레이너
    "yoga",         # 요가 마스터 수련
    "cardio",       # 유산소 전문가
    "diet",         # 영양사 민희
    # 레거시 캐릭터 (하위 호환성)
    "devil_coach",
    "angel_coach",
    "booster_coach",
]

# ================================
# 1) 자유형 챗봇
# ================================
class ChatRequest(BaseModel):
    user_id: str  # 이메일 ID
    message: str
    character: CharacterType = "default"


@router.post("/chat")
async def chat(req: ChatRequest):

    result = chat_service.handle_chat(
        user_id=req.user_id, message=req.message, character=req.character
    )

    return result


# ================================
# 2) 고정형 챗봇
# ================================
class FixedRequest(BaseModel):
    user_id: str
    question_type: str
    character: CharacterType = "default"


@router.post("/chat/fixed")
async def chat_fixed(req: FixedRequest):

    result = chat_service.handle_fixed_chat(
        user_id=req.user_id, question_type=req.question_type, character=req.character
    )

    return result
