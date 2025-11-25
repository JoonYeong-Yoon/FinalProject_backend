# JSON 처리 및 SQLAlchemy import
import json
from sqlalchemy import text
from sqlalchemy.engine import Connection

# 공통 update_record 함수 import
from .helpers import update_record

# -----------------------------
# user_info 조회 함수
# -----------------------------
def get_user_info(db: Connection, user_id: int):
    """
    특정 사용자의 user_info 조회
    - db: SQLAlchemy DB 연결 객체
    - user_id: 조회할 사용자 ID
    반환: dict 형태의 사용자 정보 또는 None
    """
    return db.execute(
        text("SELECT * FROM testing.user_info WHERE user_id = :uid"),  # SQL문
        {"uid": user_id}  # 바인딩 파라미터
    ).mappings().first()  # dict 형태로 반환

# -----------------------------
# user_info 삽입 함수
# -----------------------------
def insert_user_info(db: Connection, user_id: int, dailytime=None, weekly=None,
                     activity=None, targetperiod=None, intro=None, prefer=None):
    """
    새로운 user_info 레코드 삽입
    - db: SQLAlchemy DB 연결 객체
    - user_id: 사용자 ID
    - dailytime, weekly, activity, targetperiod, intro: 사용자 정보 필드
    - prefer: 선호 항목 리스트, JSON 문자열로 저장
    """
    db.execute(
        text("""
            INSERT INTO testing.user_info
            (user_id, dailytime, weekly, activity, targetperiod, intro, prefer)
            VALUES (:user_id, :dailytime, :weekly, :activity, :targetperiod, :intro, :prefer)
        """),
        {
            "user_id": user_id,
            "dailytime": dailytime,
            "weekly": weekly,
            "activity": activity,
            "targetperiod": targetperiod,
            "intro": intro,
            "prefer": json.dumps(prefer or []),  # 리스트 → JSON 문자열
        }
    )
    db.commit()  # DB 반영

# -----------------------------
# user_info 업데이트 함수
# -----------------------------
def update_user_info(db: Connection, user_id: int, fields: dict, insert_if_missing=False):
    """
    사용자 user_info 업데이트
    - fields: 업데이트할 필드 dict
    - insert_if_missing: True면 레코드가 없을 경우 insert 수행
    """
    # 프론트에서 전달된 camelCase 키를 DB 컬럼명 snake_case로 매핑
    if "dailyTime" in fields:
        fields["dailytime"] = fields.pop("dailyTime")
    if "targetPeriod" in fields:
        fields["targetperiod"] = fields.pop("targetPeriod")

    # 공통 update_record 사용
    update_record(
        db,
        table="testing.user_info",             # 테이블 이름
        user_id=user_id,                        # 대상 사용자 ID
        fields=fields,                          # 업데이트할 필드
        json_keys=["prefer"],                   # JSON 변환할 필드
        insert_func=insert_user_info if insert_if_missing else None  # insert 처리 함수
    )
