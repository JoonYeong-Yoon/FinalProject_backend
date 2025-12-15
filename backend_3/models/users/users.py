from sqlalchemy import text
from sqlalchemy.engine import Connection
from .tables import USERS_TABLE


def _serialize_user(row):
    """
    DB row(dict) → JSON-safe dict
    """
    user = dict(row)
    if "id" in user and user["id"] is not None:
        user["id"] = str(user["id"])
    return user


def get_user_by_email(db: Connection, email: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE email = :email"),
        {"email": email}
    ).mappings().first()

    return _serialize_user(row) if row else None


def get_user_by_id(db: Connection, user_id: str):
    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()

    return _serialize_user(row) if row else None


def create_user(db: Connection, email: str, name: str, password_hash: str):
    result = db.execute(
        text(f"""
            INSERT INTO {USERS_TABLE} (email, name, password_hash)
            VALUES (:email, :name, :password)
            RETURNING id
        """),
        {"email": email, "name": name, "password": password_hash}
    )
    
    # UUID → str
    return str(result.scalar())


def update_user(db: Connection, user_id: str, fields: dict):
    if not fields:
        return

    set_clause = ", ".join([f"{k} = :{k}" for k in fields])
    db.execute(
        text(f"UPDATE {USERS_TABLE} SET {set_clause} WHERE id = :id"),
        {**fields, "id": user_id}
    )
    db.commit()


def delete_user(db: Connection, user_id: str):
    result = db.execute(
        text(f"DELETE FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()

    if result.rowcount == 0:
        raise LookupError("USER_NOT_FOUND")
