import json
from sqlalchemy import text
from sqlalchemy.engine import Connection

from .tables import USER_INFO_TABLE
from .helpers import update_record


# -----------------------------
# user_info 조회
# -----------------------------
def get_user_info(db: Connection, user_id: int):
    return db.execute(
        text(f"SELECT * FROM {USER_INFO_TABLE} WHERE user_id = :uid"),
        {"uid": user_id}
    ).mappings().first()


# -----------------------------
# ⚠️ user_info 삽입 (회원가입에서는 절대 호출 안 됨)
# -----------------------------
def insert_user_info(db: Connection, user_id: int,
                     dailytime=None, weekly=None, activity=None,
                     targetperiod=None, intro=None, prefer=None):

    db.execute(
        text(f"""
            INSERT INTO {USER_INFO_TABLE}
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
            "prefer": json.dumps(prefer or []),
        }
    )

    db.commit()


# -----------------------------
# user_info 업데이트
# -----------------------------
def update_user_info(db: Connection, user_id: int, fields: dict, insert_if_missing=False):

    # camelCase → snake_case 변환
    if "dailyTime" in fields:
        fields["dailytime"] = fields.pop("dailyTime")
    if "targetPeriod" in fields:
        fields["targetperiod"] = fields.pop("targetPeriod")

    update_record(
        db,
        table=USER_INFO_TABLE,
        user_id=user_id,
        fields=fields,
        json_keys=["prefer"],
        insert_func=insert_user_info if insert_if_missing else None
    )
