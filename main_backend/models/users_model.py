# models/users_model.py

from sqlalchemy import text
from sqlalchemy.engine import Connection
from .tables import USERS_TABLE, USER_BODY_TABLE


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
    query = f"""
        SELECT
        u.*,

        ub.user_id AS user_body_id,
        ub.height_cm,
        ub.weight_kg,
        ub.body_fat,
        ub.skeletal_muscle,
        ub.bmr,
        ub.visceral_fat_level,
        ub.water,
        ub.bmi,
        ub.updated_at,

        s.id AS subscription_id,
        s.plan_id,
        s.status,
        s.start_date,
        s.end_date,
        s.next_billing_date,

        sp.id AS subscription_plan_id,
        sp.price,
        sp.description
    FROM {USERS_TABLE} u
    LEFT JOIN {USER_BODY_TABLE} ub
        ON u.id = ub.user_id
    LEFT JOIN subscriptions s
        ON u.id = s.user_id
    LEFT JOIN subscription_plans sp
        ON s.plan_id = sp.id
    WHERE u.id = :user_id;

    """
    row = db.execute(
        text(query),
        # text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"user_id": user_id}
    ).mappings().first()
    data = dict(row) if row else None
    print("data", data, row, user_id)
    data.pop("password_hash", None)
    data.pop("user_id", None)
    return data


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
        UPDATE {USER_BODY_TABLE}
        SET {set_clause}
        WHERE user_id = :id
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
