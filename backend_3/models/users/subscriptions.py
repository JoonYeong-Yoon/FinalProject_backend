from sqlalchemy import text
from .tables import USERS_TABLE


def set_subscription(db, email: str, is_subscribed: bool):
    result = db.execute(
        text(f"""
            UPDATE {USERS_TABLE}
            SET is_subscribed = :sub
            WHERE email = :email
        """),
        {"email": email, "sub": is_subscribed}
    )
    db.commit()

    if result.rowcount == 0:
        raise LookupError("USER_NOT_FOUND")

    return {"email": email, "is_subscribed": is_subscribed}
