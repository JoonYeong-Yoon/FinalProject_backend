from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from web.schemas import UserCreate, UserOut, Login
from web.services.hashing import password_hash, verify_password 
from web.services.oauth2 import create_access_token

router = APIRouter(tags=["Users"])

# ============================
# 회원가입
# ============================
@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist = crud.get_user_by_email(db, user.email)
    if exist:
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    new_user = crud.create_user(
        db=db,
        email=user.email,
        username=user.username,
        password=user.password
    )

    return {"email": new_user.email, "username": new_user.name}


# ============================
# 로그인
# ============================
@router.post("/login")
def login(user: Login, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user:
        raise HTTPException(status_code=400, detail="등록되지 않은 이메일입니다.")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="비밀번호가 올바르지 않습니다.")

    token = create_access_token({"email": db_user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": db_user.name
    }
