# models/user_body_model.py
from sqlalchemy import text
from sqlalchemy.engine import Connection
from .helpers import update_record
from .tables import USER_BODY_TABLE


def get_body_info(db: Connection, user_id: str):
    return db.execute(
        text(f"SELECT * FROM {USER_BODY_TABLE} WHERE user_id = :uid"),
        {"uid": user_id}
    ).mappings().first()


def insert_body_info(db: Connection, user_id: str, height_cm=None, weight_kg=None, bmi=None):
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


def update_body_info(db: Connection, user_id: str, fields: dict, insert_if_missing=False):

    update_record(
        db,
        table=USER_BODY_TABLE,
        user_id=user_id,
        fields=fields,
        json_keys=[],
        insert_func=insert_body_info if insert_if_missing else None
    )
