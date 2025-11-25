# 비밀번호 해싱 및 검증을 위한 passlib import
from passlib.context import CryptContext

# -----------------------------
# Bcrypt 해싱 컨텍스트 생성
# -----------------------------
pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated="auto")  # bcrypt 사용, 구식 옵션 자동 처리
MAX_BCRYPT_LEN = 72  # bcrypt는 최대 72바이트까지만 처리 가능

# -----------------------------
# 비밀번호 해싱 함수
# -----------------------------
def password_hash(password: str):
    """
    평문 비밀번호를 bcrypt로 해싱
    - password: 사용자 입력 비밀번호
    반환: 해시 문자열
    """
    password = password.strip()  # 공백 제거
    pw_bytes = password.encode("utf-8")  # 문자열 → 바이트

    # bcrypt 최대 길이 제한 적용
    if len(pw_bytes) > MAX_BCRYPT_LEN:
        pw_bytes = pw_bytes[:MAX_BCRYPT_LEN]

    return pwd_cxt.hash(pw_bytes)  # 해시값 반환

# -----------------------------
# 비밀번호 검증 함수
# -----------------------------
def verify_password(plain_pw: str, hashed_pw: str):
    """
    평문 비밀번호와 해시값 비교
    - plain_pw: 사용자가 입력한 비밀번호
    - hashed_pw: DB에 저장된 bcrypt 해시
    반환: True / False
    """
    pw_bytes = plain_pw.encode("utf-8")
    if len(pw_bytes) > MAX_BCRYPT_LEN:
        pw_bytes = pw_bytes[:MAX_BCRYPT_LEN]  # 최대 길이 제한

    return pwd_cxt.verify(pw_bytes, hashed_pw)  # 검증 결과 반환
