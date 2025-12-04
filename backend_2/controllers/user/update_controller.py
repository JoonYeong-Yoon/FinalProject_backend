# 외부 모듈 import
# password_hash: 비밀번호를 안전하게 해시 처리
from services.hashing_service import password_hash

# DB 모델 함수 import
from models.users_model import get_user_by_id, update_user
from models.user_body_model import get_body_info, insert_body_info, update_body_info
from models.user_info_model import get_user_info, insert_user_info, update_user_info as update_user_info_model

# 회원 정보 업데이트 함수 정의
# db: SQLAlchemy DB 세션/연결 객체
# user_id: 수정할 사용자 ID
# data: 프론트에서 전달된 수정 데이터 (dict)
def update_user_info(db, user_id: int, data: dict):
    # 1. users 테이블에서 해당 사용자 조회
    user = get_user_by_id(db, user_id)
    if not user:
        return {"error": "사용자를 찾을 수 없습니다."}  # 사용자 미존재 시 에러 반환

    # --- users 테이블 필드 업데이트 ---
    user_fields = {}  # 업데이트할 필드를 저장할 dict

    # 사용자 데이터에 따라 필드 매핑
    if "username" in data:
        user_fields["name"] = data["username"]
    if "password" in data:
        user_fields["password_hash"] = password_hash(data["password"])  # 비밀번호 해싱
    if "email" in data:
        user_fields["email"] = data["email"]
    if "phone" in data:
        user_fields["phone"] = data["phone"]
    if "age" in data:
        user_fields["age"] = data["age"]
    if "gender" in data:
        user_fields["gender"] = data["gender"]
    if "goal" in data:
        user_fields["goal"] = data["goal"]

    # 업데이트할 필드가 존재하면 DB 업데이트
    if user_fields:
        update_user(db, user_id, user_fields)

    # --- user_body_info 테이블 필드 업데이트 ---
    body_fields = {}  # 신체 정보 업데이트용 dict

    if "height" in data:
        body_fields["height_cm"] = data["height"]
    if "weight" in data:
        body_fields["weight_kg"] = data["weight"]
    if "pain" in data:
        body_fields["pain"] = data["pain"]

    # 키와 몸무게가 존재하면 BMI 계산
    if body_fields:
        # 기존 DB 값 혹은 새로 들어온 값 사용, 없으면 0으로 초기화
        h = body_fields.get("height_cm") or user.get("height_cm") or 0
        w = body_fields.get("weight_kg") or user.get("weight_kg") or 0
        if h > 0 and w > 0:
            # BMI = 몸무게(kg) / (키(m)^2), 소수점 1자리로 반올림
            body_fields["bmi"] = round(w / ((h / 100) ** 2), 1)

        # 기존 user_body_info 존재 여부 확인 후 업데이트 또는 INSERT
        existing_body = get_body_info(db, user_id)
        if existing_body:
            update_body_info(db, user_id, body_fields)
        else:
            insert_body_info(
                db,
                user_id,
                body_fields.get("height_cm", 0),
                body_fields.get("weight_kg", 0),
                body_fields.get("bmi", 0)
            )

    # --- user_info 테이블 업데이트 ---
    info_fields = {}  # 운동/생활 정보 업데이트용 dict

    # 프론트에서 전달된 데이터 키에 따라 필드 매핑
    if "dailyTime" in data:
        info_fields["dailytime"] = data["dailyTime"]
    if "weekly" in data:
        info_fields["weekly"] = data["weekly"]
    if "activity" in data:
        info_fields["activity"] = data["activity"]
    if "targetPeriod" in data:
        info_fields["targetperiod"] = data["targetPeriod"]
    if "intro" in data:
        info_fields["intro"] = data["intro"]
    if "prefer" in data:
        info_fields["prefer"] = data["prefer"]

    # 업데이트할 정보가 존재하면 처리
    if info_fields:
        existing_info = get_user_info(db, user_id)
        if existing_info:
            # user_info가 이미 존재하면 update
            update_user_info_model(db, user_id, info_fields)
        else:
            # user_info가 없으면 새로 insert
            insert_user_info(
                db, 
                user_id,
                dailytime=info_fields.get("dailytime"),
                weekly=info_fields.get("weekly"),
                activity=info_fields.get("activity"),
                targetperiod=info_fields.get("targetperiod"),
                intro=info_fields.get("intro"),
                prefer=info_fields.get("prefer")                
            )

        # 최종 성공 메시지 반환
        return {"message": "회원정보가 수정되었습니다."}
