from models.users.users import update_user
from models.users.user_profile import update_user_info, update_body_info


def update_profile(db, user_id: str, data: dict):
    user_fields = {}
    info_fields = {}
    body_fields = {}

    # -------------------------
    # users 테이블
    # -------------------------
    for key in ["name", "phone", "age", "gender", "goal", "avatar"]:
        if key in data:
            user_fields[key] = data[key]

    # -------------------------
    # user_info 테이블
    # -------------------------
    for key in ["dailyTime", "weekly", "activity", "targetPeriod", "intro", "prefer"]:
        if key in data:
            info_fields[key] = data[key]

    # -------------------------
    # user_body 테이블
    # -------------------------
    if "height" in data:
        body_fields["height_cm"] = data["height"]
    if "weight" in data:
        body_fields["weight_kg"] = data["weight"]

    if "height" in data and "weight" in data:
        h = data["height"]
        w = data["weight"]
        if h and w:
            body_fields["bmi"] = round(w / ((h / 100) ** 2), 1)

    # -------------------------
    # DB 반영
    # -------------------------
    if user_fields:
        update_user(db, user_id, user_fields)

    if info_fields:
        update_user_info(db, user_id, info_fields)

    if body_fields:
        update_body_info(db, user_id, body_fields)

    return {"message": "프로필 수정 완료"}
