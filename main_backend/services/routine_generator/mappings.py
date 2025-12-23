# ===============================================================
#  Korean <-> English Mapping for Exercise AI Platform
#  - 모든 DB 저장 값은 영어
#  - 프론트에서는 한국어 사용 가능
#  - 백엔드에서 한국어 입력이 들어올 경우 영어로 변환할 수 있도록 구성
# ===============================================================

# -----------------------------
# 한국어 ↔ 영어 매핑 테이블들
# -----------------------------
# ---------------------------------------------------------------
# 1) EXERCISE NAME (17개)
# ---------------------------------------------------------------
EXERCISE_KO_TO_EN = {
    "스탠딩 사이드 크런치": "standing_side_crunch",
    "스탠딩 니업": "standing_knee_up",
    "버피 테스트": "burpee_test",
    "스텝 포워드 다이나믹 런지": "step_forward_dynamic_lunge",
    "스텝 백워드 다이나믹 런지": "step_backward_dynamic_lunge",
    "사이드 런지": "side_lunge",
    "크로스 런지": "cross_lunge",
    "굿모닝": "good_morning",
    "라잉 레그 레이즈": "lying_leg_raise",
    "크런치": "crunch",
    "바이시클 크런치": "bicycle_crunch",
    "시저 크로스": "scissor_cross",
    "힙 쓰러스트": "hip_thrust",
    "플랭크": "plank",
    "푸시업": "push_up",
    "니 푸시업": "knee_push_up",
    "와이 엑서사이즈": "y_exercise",
}

EXERCISE_EN_TO_KO = {v: k for k, v in EXERCISE_KO_TO_EN.items()}

# ---------------------------------------------------------------
# 2) GOAL (사용자 운동 목적)
# ---------------------------------------------------------------
GOAL_KO_TO_EN = {
    "체중 감량": "FAT_LOSS",
    "근육 증가": "MUSCLE_GAIN",
    "지구력 향상": "ENDURANCE",
    "기초체력 유지": "MAINTAIN",
}
GOAL_EN_TO_KO = {v: k for k, v in GOAL_KO_TO_EN.items()}


# ---------------------------------------------------------------
# 3) INJURY AREA (부상 부위)
# ---------------------------------------------------------------
INJURY_KO_TO_EN = {
    "어깨": "SHOULDER",
    "팔꿈치": "ELBOW",
    "허리": "WAIST",
    "무릎": "KNEE",
    "발목": "ANKLE",
    "기타": "ETC",
}
INJURY_EN_TO_KO = {v: k for k, v in INJURY_KO_TO_EN.items()}

INJURY_EXERCISE_MAP = {
    "SHOULDER": {"burpee_test", "plank", "push_up", "knee_push_up", "y_exercise"},
    "ELBOW": {"burpee_test", "plank", "push_up", "knee_push_up"},
    "WAIST": {"standing_side_crunch", "burpee_test", "good_morning", "lying_leg_raise", "crunch", 
              "bicycle_crunch", "scissor_cross", "hip_thrust", "plank", "push_up", "knee_push_up", "y_exercise"},
    "KNEE": {"burpee_test", "step_forward_dynamic_lunge", "step_backward_dynamic_lunge", "side_lunge",
             "cross_lunge", "good_morning"},
    "ANKLE": {"burpee_test", "side_lunge", "cross_lunge", "good_morning"},
    "ETC": set(),
}

# ---------------------------------------------------------------
# 4) CANCELLATION REASON (루틴 취소 이유)
# ---------------------------------------------------------------
CANCEL_KO_TO_EN = {
    "너무 힘듦": "TOO_HARD",
    "너무 김": "TOO_LONG",
    "부상": "INJURY",
    "외부 방해": "INTERRUPTED",   # 다음 추천에 반영 X (특수 규칙)
}
CANCEL_EN_TO_KO = {v: k for k, v in CANCEL_KO_TO_EN.items()}


# ---------------------------------------------------------------
# 5) category_1 (운동 부위)
# ---------------------------------------------------------------
CATEGORY1_KO_TO_EN = {
    "상체": "UPPER_BODY",
    "하체": "LOWER_BODY",
    "코어": "CORE",
    "전신": "FULL_BODY",
}
CATEGORY1_EN_TO_KO = {v: k for k, v in CATEGORY1_KO_TO_EN.items()}


# ---------------------------------------------------------------
# 6) Routine Status (activity_logs.status)
# ---------------------------------------------------------------
STATUS_KO_TO_EN = {
    "완료": "FINISHED",
    "취소": "CANCELED",
    "대기": "WAITING",
    "진행": "IN_PROGRESS"
}
STATUS_EN_TO_KO = {v: k for k, v in STATUS_KO_TO_EN.items()}


# ---------------------------------------------------------------
# 7) user_body_info Labels (프론트 출력용)
# ---------------------------------------------------------------
USER_BODY_INFO_LABELS = {
    "height_cm": "키(cm)",
    "weight_kg": "몸무게(kg)",
    "body_fat": "체지방률(%)",
    "skeletal_muscle": "골격근량(kg)",
    "bmi": "BMI",
    "bmr": "기초대사량(kcal)",
    "visceral_fat_level": "내장지방 레벨(1~20)",
    "water": "체수분"
}

# --------------------
# 변환 유틸
# --------------------
def map_ko_to_en(value: str, mapping: dict) -> str:
    if value is None:
        return value
    return mapping.get(value, value)

def map_en_to_ko(value: str, mapping: dict) -> str:
    if value is None:
        return value
    return mapping.get(value, value)

