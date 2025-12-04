# SQLAlchemy import
from sqlalchemy import text
from sqlalchemy.engine import Connection

# tables에 정의된 db의 테이블 불러오기
from .tables import USERS_TABLE

# -----------------------------
# 이메일로 사용자 조회
# -----------------------------
def get_user_by_email(db: Connection, email: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE email = :email"),
        {"email": email}
    ).mappings().first()
    return dict(row) if row else None

# -----------------------------
# ID로 사용자 조회
# -----------------------------
def get_user_by_id(db: Connection, user_id: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()
    return dict(row) if row else None

# -----------------------------
# 새로운 사용자 삽입
# -----------------------------
def insert_user(db, email, name, password_hash, goal=None):
    result = db.execute(
        text(f"""
            INSERT INTO {USERS_TABLE} (email, name, password_hash, goal)
            VALUES (:email, :name, :password, :goal)
            RETURNING id
        """),
        {"email": email, "name": name, "password": password_hash, "goal": goal}
    )
    db.commit()
    return result.scalar()

# -----------------------------
# 🔵 기본 사용자 정보 업데이트 (프론트 프로필 수정용)
# -----------------------------
def update_basic_user(db: Connection, user_id: str, fields: dict):
    """
    name, email, phone, age, gender, goal, avatar 등 기본 user 테이블 업데이트
    """
    if not fields:
        return

    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
    params = fields.copy()
    params["id"] = user_id

    db.execute(
        text(f"UPDATE {USERS_TABLE} SET {set_clause} WHERE id = :id"),
        params
    )
    db.commit()

# -----------------------------
# 사용자 삭제
# -----------------------------
def delete_user(db: Connection, user_id: str):
    db.execute(
        text(f"DELETE FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()


# =============================
# 회원가입용 Pydantic 모델
# =============================
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    username: str
    password: str


# =============================
# 🔥 옛 코드 호환성 —
# update_user 를 찾는 코드가 많아서 alias로 연결
# =============================
update_user = update_basic_user
