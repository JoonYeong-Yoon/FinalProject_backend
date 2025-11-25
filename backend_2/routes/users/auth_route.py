# FastAPI 관련 import
from fastapi import APIRouter, Depends, HTTPException, Body

# DB 연결 및 컨트롤러 import
from db.database import get_db
from controllers.user.register_controller import register_user
from controllers.user.login_controller import login_user
from services.oauth2_service import create_access_token  # JWT 토큰 생성

# -----------------------------
# 인증 관련 라우터 생성
# -----------------------------
router = APIRouter(tags=["auth"])  # Swagger UI에서 그룹화

# -----------------------------
# 회원가입 엔드포인트
# -----------------------------
@router.post("/register")
async def register(user: dict = Body(...), db=Depends(get_db)):
    """
    회원가입 처리
    - user: 요청 바디로 전달된 사용자 정보(dict)
    - db: DB 연결 (Depends 사용)
    반환: 성공 시 사용자 이메일/이름 dict, 실패 시 HTTPException 400
    """
    res = register_user(user, db)  # 컨트롤러 호출
    if "error" in res:             # 에러 처리
        raise HTTPException(status_code=400, detail=res["error"])
    return res                     # 성공 시 사용자 정보 반환

# -----------------------------
# 로그인 엔드포인트
# -----------------------------
@router.post("/login")
async def login(user: dict = Body(...), db=Depends(get_db)):
    """
    로그인 처리
    - user: 요청 바디로 전달된 이메일/비밀번호 dict
    - db: DB 연결 (Depends 사용)
    반환: JWT access_token, token_type, 사용자 이름
    """
    res = login_user(user, db)     # 컨트롤러 호출
    if "error" in res:             # 인증 실패 시
        raise HTTPException(status_code=400, detail=res["error"])

    # JWT 토큰 생성
    token = create_access_token({"email": res["email"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": res["name"]
    }
