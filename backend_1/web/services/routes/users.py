from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from schemas import UserCreate, UserOut, Login
import db.crud as crud
from services.oauth2 import create_access_token
from services.hashing import verify

router = APIRouter(prefix="/users", tags=["Users"])

# 회원가입
@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist = crud.get_user_by_email(db, user.email)
    if exist:
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    # ⭐ username 추가된 create_user에 맞게 수정
    new_user = crud.create_user(
        db=db,
        email=user.email,
        username=user.username,   # ← 추가
        password=user.password
    )
    return new_user


# 로그인
@router.post("/login")
def login(user: Login, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user:
        raise HTTPException(status_code=400, detail="등록되지 않은 이메일입니다.")

    if not verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="비밀번호가 올바르지 않습니다.")

    token = create_access_token({"user_id": db_user.id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": db_user.username   # ⭐ 프론트에서 쓰고 싶으면 이렇게 넣으면 됨!
    }
