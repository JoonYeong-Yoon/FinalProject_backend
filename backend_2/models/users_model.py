# SQLAlchemy import
from sqlalchemy import text
from sqlalchemy.engine import Connection

# tables에 정의된 db의 테이블 불러오기
from .tables import USERS_TABLE

# -----------------------------
# 이메일로 사용자 조회
# -----------------------------
def get_user_by_email(db: Connection, email: str):
    """
    이메일 기준으로 users 테이블에서 사용자 조회
    - db: SQLAlchemy DB 연결 객체
    - email: 조회할 사용자 이메일
    반환: dict 형태의 사용자 정보 또는 None
    """
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE email = :email"),
        {"email": email}  # 바인딩 파라미터
    ).mappings().first()  # dict 형태로 변환
    return dict(row) if row else None

# -----------------------------
# ID로 사용자 조회
# -----------------------------
def get_user_by_id(db: Connection, user_id: str):
    """
    ID 기준으로 users 테이블에서 사용자 조회
    - db: SQLAlchemy DB 연결 객체
    - user_id: 조회할 사용자 ID
    반환: dict 형태의 사용자 정보 또는 None
    """
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}  # 바인딩 파라미터
    ).mappings().first()
    return dict(row) if row else None

# -----------------------------
# 새로운 사용자 삽입
# -----------------------------
def insert_user(db, email, name, password_hash, goal=None):
    """
    users 테이블에 새 사용자 추가
    - db: SQLAlchemy DB 연결 객체
    - email: 사용자 이메일
    - name: 사용자 이름
    - password_hash: 해시된 비밀번호
    - goal: 사용자 목표 (옵션)
    반환: 삽입된 사용자 ID
    """
    result = db.execute(
        text("""
            INSERT INTO {USERS_TABLE} (email, name, password_hash, goal)
            VALUES (:email, :name, :password, :goal)
            RETURNING id
        """),
        {"email": email, "name": name, "password": password_hash, "goal": goal}
    )
    db.commit()  # DB 반영
    return result.scalar()  # 삽입된 ID 반환

# -----------------------------
# 사용자 정보 업데이트
# -----------------------------
def update_user(db: Connection, user_id: str, fields: dict):
    """
    users 테이블 업데이트
    - db: SQLAlchemy DB 연결 객체
    - user_id: 업데이트할 사용자 ID
    - fields: 업데이트할 필드 dict
    """
    # SET 절 생성
    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
    params = fields.copy()
    params["id"] = user_id  # WHERE 조건용 ID
    db.execute(
        text(f"UPDATE {USERS_TABLE} SET {set_clause} WHERE id = :id"),
        params
    )
    db.commit()  # DB 반영

# -----------------------------
# 사용자 삭제
# -----------------------------
def delete_user(db: Connection, user_id: str):
    """
    users 테이블에서 특정 사용자 삭제
    - db: SQLAlchemy DB 연결 객체
    - user_id: 삭제할 사용자 ID
    """
    db.execute(
        text(f"DELETE FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()
