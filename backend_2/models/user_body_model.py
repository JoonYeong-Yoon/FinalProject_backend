# JSON 처리 및 SQLAlchemy import
import json
from sqlalchemy import text
from sqlalchemy.engine import Connection

# 공통 update_record 함수 import
from .helpers import update_record

# -----------------------------
# user_body_info 조회 함수
# -----------------------------
def get_body_info(db: Connection, user_id: int):
    """
    특정 사용자의 신체 정보(user_body_info) 조회
    - db: SQLAlchemy DB 연결 객체
    - user_id: 조회할 사용자 ID
    반환: dict 형태의 사용자 신체 정보 또는 None
    """
    return db.execute(
        text("SELECT * FROM testing.user_body_info WHERE user_id = :uid"),  # SQL 문자열
        {"uid": user_id}  # 바인딩 파라미터
    ).mappings().first()  # dict 형태로 반환

# -----------------------------
# user_body_info 삽입 함수
# -----------------------------
def insert_body_info(db: Connection, user_id: int, height_cm: float, weight_kg: float, bmi: float, pain=None):
    """
    새로운 사용자 신체 정보 삽입
    - db: SQLAlchemy DB 연결 객체
    - user_id: 사용자 ID
    - height_cm: 키(cm)
    - weight_kg: 몸무게(kg)
    - bmi: BMI 값
    - pain: 통증 정보 리스트 (JSON으로 저장)
    """
    db.execute(
        text("""
        INSERT INTO testing.user_body_info 
        (user_id, height_cm, weight_kg, bmi, pain)
        VALUES (:user_id, :height_cm, :weight_kg, :bmi, :pain)
        """),
        {
            "user_id": user_id,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": bmi,
            "pain": json.dumps(pain or []),  # 리스트를 JSON 문자열로 변환
        }
    )
    db.commit()  # DB 반영

# -----------------------------
# user_body_info 업데이트 함수
# -----------------------------
def update_body_info(db: Connection, user_id: int, fields: dict, insert_if_missing=False):
    """
    사용자 신체 정보 업데이트
    - fields: 업데이트할 필드 dict (예: {"height_cm": 180, "weight_kg": 70})
    - insert_if_missing: True면 레코드 없을 경우 insert 수행
    """
    update_record(
        db,
        table="testing.user_body_info",  # 테이블 이름
        user_id=user_id,                 # 대상 사용자 ID
        fields=fields,                   # 업데이트할 필드
        json_keys=["pain"],              # JSON 변환할 필드
        insert_func=insert_body_info if insert_if_missing else None  # insert 처리 함수
    )
