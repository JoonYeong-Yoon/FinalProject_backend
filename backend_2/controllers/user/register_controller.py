# 외부 모듈 import
# password_hash: 평문 비밀번호를 해시값으로 변환
from services.hashing_service import password_hash

# DB 모델 함수 import
from models.users_model import get_user_by_email, insert_user
from models.user_info_model import insert_user_info

# 회원가입 처리 함수 정의
# user_data: 프론트에서 전달된 사용자 정보 (예: {"email": ..., "username": ..., "password": ...})
# db: SQLAlchemy DB 세션 또는 연결 객체
def register_user(user_data: dict, db):
    # 1. 이메일 중복 확인
    existing = get_user_by_email(db, user_data["email"])
    if existing:
        return {"error": "이미 존재하는 이메일입니다."}  # 이미 존재하면 에러 반환

    # 2. 비밀번호 해싱
    # 평문 비밀번호를 안전하게 저장할 수 있도록 해시값으로 변환
    hashed_pw = password_hash(user_data["password"])

    # 3. 새로운 사용자 DB에 삽입
    # insert_user: users 테이블에 새로운 레코드 생성
    # 반환값: 새로 생성된 사용자 id
    new_user_id = insert_user(db, user_data["email"], user_data["username"], hashed_pw)

    # 4. 회원가입 시 user_info 초기 레코드 생성
    # insert_user_info: user_info 테이블에 기본 레코드 추가
    insert_user_info(db, user_id=new_user_id)

    # 5. 회원가입 성공 시 사용자 이메일과 이름 반환
    return {"email": user_data["email"], "username": user_data["username"]}
