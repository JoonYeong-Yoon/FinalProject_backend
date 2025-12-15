from services.users.hashing import verify_password
from models.users.users import get_user_by_email


def login_user(data: dict, db):
    if "email" not in data or "password" not in data:
        raise ValueError("INVALID_REQUEST")

    user = get_user_by_email(db, data["email"])
    if not user:
        raise LookupError("USER_NOT_FOUND")

    if not verify_password(data["password"], user["password_hash"]):
        raise ValueError("INVALID_PASSWORD")

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"] if user.get("role") else "user"
    }
