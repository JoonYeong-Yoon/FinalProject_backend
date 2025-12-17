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

    # bcrypt 최대 길이 제한 적용
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > MAX_BCRYPT_LEN:
        # 길이가 넘으면 자른 다음 문자열로 다시 복원
        password = pw_bytes[:MAX_BCRYPT_LEN].decode("utf-8", errors="ignore")

    return pwd_cxt.hash(password)  # bcrypt는 문자열(str) 넣어야 함


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

    # 길이 초과 시 잘라냄
    pw_bytes = plain_pw.encode("utf-8")
    if len(pw_bytes) > MAX_BCRYPT_LEN:
        plain_pw = pw_bytes[:MAX_BCRYPT_LEN].decode("utf-8", errors="ignore")

    # bcrypt 검증
    return pwd_cxt.verify(plain_pw, hashed_pw)
