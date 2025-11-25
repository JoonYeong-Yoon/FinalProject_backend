# 외부 모듈 import
# verify_password: 입력한 평문 비밀번호와 DB에 저장된 해시값을 비교
from services.hashing_service import verify_password

# get_user_by_email: 이메일을 기반으로 DB에서 사용자 정보 조회
from models.users_model import get_user_by_email

# 로그인 처리 함수 정의
# data: 프론트에서 전달된 로그인 정보 (dict, 예: {"email": ..., "password": ...})
# db: SQLAlchemy DB 세션 또는 연결 객체
def login_user(data: dict, db):
    # 1. 이메일을 기준으로 DB에서 사용자 정보 조회
    user = get_user_by_email(db, data["email"])
    
    # 2. 사용자가 존재하지 않으면 에러 반환
    if not user:
        return {"error": "등록되지 않은 이메일입니다."}  # 이메일 미등록 시 메시지
    
    # 3. 비밀번호 검증
    # verify_password: 입력한 평문 비밀번호와 DB에 저장된 해시값 비교
    if not verify_password(data["password"], user["password_hash"]):
        return {"error": "비밀번호가 올바르지 않습니다."}  # 비밀번호 불일치 시 메시지
    
    # 4. 모든 검증 통과 시 사용자 정보 반환
    # 반환값 예: {"id": UUID로 암호화된 문자열, "email": "test@test.com", "name": "홍길동", ...}
    return user
