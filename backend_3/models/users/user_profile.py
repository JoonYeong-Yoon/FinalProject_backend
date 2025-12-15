import json
from sqlalchemy import text
from sqlalchemy.engine import Connection

from .tables import USER_BODY_TABLE
from .utils.update import update_or_insert


def get_profile_info(db: Connection, user_id: str):
    body = db.execute(
        text(f"SELECT * FROM {USER_BODY_TABLE} WHERE user_id = :uid"),
        {"uid": user_id}
    ).mappings().first()
    
    info = dict(info)
    body = dict(body)
    
    info["prefer"] = json.loads(info["prefer"]) if info.get("prefer") else []

    return info, body

def insert_body_info(db, user_id, height_cm: float, weight_kg: float, bmi: float = 0):
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
            "bmi": bmi
        }
    )


def update_user_info(db: Connection, user_id: str, fields: dict):
    update_or_insert(
        db,
        
        user_id,
        fields,
        json_keys=["prefer"]
    )


def update_body_info(db: Connection, user_id: str, fields: dict):
    update_or_insert(
        db,
        USER_BODY_TABLE,
        user_id,
        fields,
        insert_func=insert_body_info
    )
