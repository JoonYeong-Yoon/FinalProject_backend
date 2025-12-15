from services.users.hashing import password_hash
from models.users.users import get_user_by_email, create_user
from models.users.user_profile import insert_body_info

def register_user(user_data: dict, db):
    required = ["email", "password", "username"]
    if not all(k in user_data for k in required):
        raise ValueError("INVALID_REQUEST")

    if get_user_by_email(db, user_data["email"]):
        raise ValueError("EMAIL_ALREADY_EXISTS")

    hashed_pw = password_hash(user_data["password"])
    try:
        user_id = create_user(
            db,
            email=user_data["email"],
            name=user_data["username"],
            password_hash=hashed_pw
        )
        
        insert_body_info(
            db,
            user_id = user_id,
            height_cm = 0,
            weight_kg = 0,
            bmi = 0
        )
        
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": str(user_id),
        "email": user_data["email"],
        "name": user_data["username"]
    }
