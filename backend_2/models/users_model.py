# models/users_model.py

from sqlalchemy import text
from sqlalchemy.engine import Connection
from .tables import USERS_TABLE


# ===========================
# 1) 이메일로 사용자 조회
# ===========================
def get_user_by_email(db: Connection, email: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE email = :email"),
        {"email": email}
    ).mappings().first()
    return dict(row) if row else None


# ===========================
# 2) ID로 사용자 조회
# ===========================
def get_user_by_id(db: Connection, user_id: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()
    return dict(row) if row else None


# ===========================
# 3) 회원가입: 사용자 추가
# ===========================
def insert_user(db: Connection, email: str, name: str, password_hash: str, goal=None):
    result = db.execute(
        text(f"""
            INSERT INTO {USERS_TABLE} (email, name, password_hash, goal)
            VALUES (:email, :name, :password, :goal)
            RETURNING id
        """),
        {
            "email": email,
            "name": name,
            "password": password_hash,
            "goal": goal,
        }
    )
    db.commit()
    return result.scalar()


# ===========================
# ⭐ 4) 기본정보 업데이트 (선택)
# profile_route에서는 raw SQL 사용하므로 필수 아님
# ===========================
def update_basic_user(db: Connection, user_id: str, fields: dict):
    """
    users 테이블 기본 필드 업데이트 (name, email, phone, age 등)
    """
    if not fields:
        return

    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])

    sql = text(f"""
        UPDATE {USERS_TABLE}
        SET {set_clause}
        WHERE id = :id
    """)

    db.execute(sql, {**fields, "id": user_id})
    db.commit()


# ===========================
# ⭐ 5) 사용자 삭제 (관리자/본인탈퇴용)
# ===========================
def delete_user(db: Connection, user_id: str):
    db.execute(
        text(f"DELETE FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()
