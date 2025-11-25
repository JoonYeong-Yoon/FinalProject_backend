# FastAPI 관련 import
from fastapi import APIRouter, Depends, HTTPException, Body

# DB 연결 및 모델/컨트롤러 import
from db.database import get_db
from services.oauth2_service import get_current_user  # 현재 로그인 사용자 확인
from models.users_model import get_user_by_email
from models.user_body_model import get_body_info
from models.user_info_model import get_user_info
from controllers.user.update_controller import update_user_info  # 사용자 정보 업데이트 로직

# -----------------------------
# 사용자 프로필 라우터 생성
# -----------------------------
router = APIRouter(tags=["profile"])  # Swagger UI에서 그룹화

# -----------------------------
# 내 정보 조회 엔드포인트
# -----------------------------
@router.get("/me")
async def get_my_info(current_user=Depends(get_current_user), db=Depends(get_db)):
    """
    현재 로그인한 사용자의 전체 정보 조회
    - current_user: JWT 토큰 기반 인증 사용자
    - db: DB 연결
    반환: 사용자 정보 dict (users / user_body_info / user_info 통합)
    """
    # 1. users 테이블에서 기본 정보 조회
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 2. user_body_info 조회 (키, 몸무게, 통증 등)
    body = get_body_info(db, user["id"])

    # 3. user_info 조회 (운동 목표, 주간 계획 등)
    info = get_user_info(db, user["id"])

    # 4. 가입일 처리 (datetime → "YYYY-MM-DD" 문자열)
    created_at = user.get("created_at")
    if created_at:
        try:
            created_at = created_at.strftime("%Y-%m-%d")
        except:
            created_at = str(created_at)[:10]  # fallback 문자열 처리

    # 5. 통합 정보 반환
    return {
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "age": user.get("age"),
        "gender": user.get("gender"),
        "height": body.get("height_cm") if body else None,
        "weight": body.get("weight_kg") if body else None,
        "pain": body.get("pain") if body else [],
        "goal": user.get("goal"),
        "avatar": user.get("avatar"),
        "dailyTime": info.get("dailytime") if info else None,
        "weekly": info.get("weekly") if info else None,
        "activity": info.get("activity") if info else None,
        "targetPeriod": info.get("targetperiod") if info else None,
        "intro": info.get("intro") if info else None,
        "prefer": info.get("prefer") if info else [],
        "created_at": created_at
    }

# -----------------------------
# 내 정보 수정 엔드포인트
# -----------------------------
@router.put("/update")
async def update_user(current_user=Depends(get_current_user), db=Depends(get_db), body: dict = Body(...)):
    """
    현재 로그인한 사용자의 정보 수정
    - body: 수정할 필드 dict
    - db: DB 연결
    - current_user: JWT 인증 사용자
    반환: 수정 완료 메시지 또는 에러
    """
    # 1. 사용자 조회
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 2. 컨트롤러 호출하여 업데이트
    res = update_user_info(db, user["id"], body)
    if "error" in res:  # 에러 처리
        raise HTTPException(status_code=400, detail=res["error"])

    return res  # 수정 완료 메시지 반환
