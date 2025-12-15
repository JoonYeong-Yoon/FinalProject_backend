from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
MAX_BCRYPT_LEN = 72


def password_hash(password: str) -> str:
    password = password.strip()
    pw_bytes = password.encode("utf-8")

    if len(pw_bytes) > MAX_BCRYPT_LEN:
        password = pw_bytes[:MAX_BCRYPT_LEN].decode("utf-8", errors="ignore")

    return pwd_ctx.hash(password)


def verify_password(plain_pw: str, hashed_pw: str) -> bool:
    pw_bytes = plain_pw.encode("utf-8")

    if len(pw_bytes) > MAX_BCRYPT_LEN:
        plain_pw = pw_bytes[:MAX_BCRYPT_LEN].decode("utf-8", errors="ignore")

    return pwd_ctx.verify(plain_pw, hashed_pw)
