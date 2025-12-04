# ============================================
# 🚀 user_body_model.py — pain 제거 완료 버전
# ============================================

import json
from sqlalchemy import text
from sqlalchemy.engine import Connection

# 공통 update_record 함수
from .helpers import update_record

# 테이블 이름 불러오기
from .tables import USER_BODY_TABLE


# --------------------------------------------
# 🟦 1) user_body_info 조회
# --------------------------------------------
def get_body_info(db: Connection, user_id: str):
    """
    특정 사용자의 신체 정보 조회
    """
    return db.execute(
        text(f"SELECT * FROM {USER_BODY_TABLE} WHERE user_id = :uid"),
        {"uid": user_id}
    ).mappings().first()


# --------------------------------------------
# 🟩 2) user_body_info 신규 생성
# --------------------------------------------
def insert_body_info(db: Connection, user_id: str, height_cm=None, weight_kg=None, bmi=None):
    """
    body_info 신규 삽입
    """
    db.execute(
        text(f"""
        INSERT INTO {USER_BODY_TABLE}
        (user_id, height_cm, weight_kg, bmi)
        VALUES (:user_id, :height_cm, :weight_kg, :bmi)
        """),
        {
            "user_id": user_id,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": bmi,
        }
    )
    db.commit()


# --------------------------------------------
# 🟧 3) user_body_info 업데이트
# --------------------------------------------
def update_body_info(db: Connection, user_id: str, fields: dict, insert_if_missing=False):
    """
    height_cm, weight_kg, bmi 같은 신체 정보만 업데이트
    """

    # JSON 컬럼 없으므로 json_keys=[] 로 둔다
    update_record(
        db,
        table=USER_BODY_TABLE,
        user_id=user_id,
        fields=fields,
        json_keys=[],                     # ← pain 제거!
        insert_func=insert_body_info if insert_if_missing else None
    )
