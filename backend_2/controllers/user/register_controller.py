# 외부 모듈 import
from services.hashing_service import password_hash

# DB 모델 함수 import
from models.users_model import get_user_by_email, insert_user
from models.user_info_model import insert_user_info


def register_user(user_data: dict, db):
    """
    회원가입 처리 함수
    user_data = { "email": ..., "name": ..., "password": ..., "goal": ... }
    """

    # 1) 이메일 중복 체크
    existing = get_user_by_email(db, user_data["email"])
    if existing:
        return {"error": "이미 존재하는 이메일입니다."}

    # 2) 비밀번호 해싱
    hashed_pw = password_hash(user_data["password"])

    # 3) users 테이블에 사용자 생성
    # insert_user(email, name, hashed_pw, goal)
    new_user_id = insert_user(
        db,
        user_data["email"],
        user_data["name"],     # ✔ username → name으로 수정
        hashed_pw,
        user_data.get("goal")  # goal은 선택값
    )

    # 4) user_info 초기 레코드 생성 (선택)
    # 필요하면 아래 줄을 활성화 가능
    # insert_user_info(db, user_id=new_user_id)

    # 5) 성공 응답 반환
    return {
        "id": new_user_id,
        "email": user_data["email"],
        "name": user_data["name"]
    }
