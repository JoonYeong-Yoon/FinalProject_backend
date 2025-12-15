import json
from sqlalchemy import text
from sqlalchemy.engine import Connection


def build_set_clause(fields: dict):
    return ", ".join([f"{k} = :{k}" for k in fields.keys()])


def update_or_insert(
    db: Connection,
    table: str,
    user_id: str,
    fields: dict,
    json_keys=None,
    insert_func=None
):
    json_keys = json_keys or []

    for key in json_keys:
        if key in fields:
            fields[key] = json.dumps(fields[key] or [])

    exists = db.execute(
        text(f"SELECT 1 FROM {table} WHERE user_id = :uid"),
        {"uid": user_id}
    ).first()

    if not exists:
        if insert_func:
            insert_func(db, user_id, **fields)
        return

    set_clause = build_set_clause(fields)
    db.execute(
        text(f"UPDATE {table} SET {set_clause} WHERE user_id = :user_id"),
        {**fields, "user_id": user_id}
    )
    db.commit()
