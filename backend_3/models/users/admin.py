from sqlalchemy import text
from .tables import USERS_TABLE


def get_all_users(db):
    rows = db.execute(
        text(f"SELECT * FROM {USERS_TABLE}")
    ).mappings().all()
    return [dict(r) for r in rows]


def get_user_detail(db, user_id: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()

    if not row:
        raise LookupError("USER_NOT_FOUND")

    return dict(row)


def update_user_role(db, user_id: str, role: str):
    if role not in ("admin", "user"):
        raise ValueError("INVALID_ROLE")

    db.execute(
        text(f"""
            UPDATE {USERS_TABLE}
            SET role = :role
            WHERE id = :id
        """),
        {"role": role, "id": user_id}
    )
    db.commit()


def delete_user_admin(db, user_id: str):
    result = db.execute(
        text(f"DELETE FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()

    if result.rowcount == 0:
        raise LookupError("USER_NOT_FOUND")
