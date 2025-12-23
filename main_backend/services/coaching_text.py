"""
코칭 문장 생성 모듈
- 실시간 자세 분석 없음 (현 단계)
- TTS 안정성을 고려한 짧고 명확한 문장 사용
- 서비스 흐름 중심 (루틴 시작 → 세트 안내 → 종료)
"""

from typing import Dict


# ===============================
# 루틴 시작
# ===============================
def generate_start_text(first_exercise: Dict) -> str:
    """
    루틴 + 첫 운동 시작 안내
    """
    exercise_name = first_exercise.get("name", "운동")

    return (
        "운동을 시작하기 전에 충분히 스트레칭을 해주세요. "
        f"준비되셨으면 {exercise_name} 1세트를 시작합니다."
    )

# ===============================
# 운동 시작 전 안내
# ===============================
def generate_exercise_intro_text(exercise: dict) -> str:
    """
    운동 시작 시 1회 안내 (설명 + 주의)
    """
    parts = []

    if exercise.get("description"):
        parts.append(exercise["description"].strip())

    if exercise.get("caution"):
        parts.append("Please be careful. " + exercise["caution"].strip())

    return " ".join(parts)

# ===============================
# 다음 세트 / 다음 운동 안내
# ===============================
def generate_next_text(exercise: Dict, set_number: int) -> str:
    """
    다음 세트 또는 다음 운동 시작 안내
    """
    exercise_name = exercise.get("name", "운동")

    return (
        f"{exercise_name} {set_number}세트입니다. "
        "호흡을 유지하면서 진행해 주세요."
    )


# ===============================
# 휴식 안내 (선택적)
# ===============================
def generate_rest_text(rest_sec: int) -> str:
    """
    세트 간 휴식 안내
    """
    if not rest_sec or rest_sec <= 0:
        return "잠깐 휴식하세요."

    return f"{rest_sec}초 간 휴식하세요. 호흡을 정리해 주세요."


# ===============================
# 루틴 종료
# ===============================
def generate_finish_text(completion_ratio: float) -> str:
    """
    루틴 종료 안내
    """
    percent = int(completion_ratio * 100)

    if percent >= 90:
        message = "아주 훌륭해요."
    elif percent >= 70:
        message = "잘 해내셨어요."
    else:
        message = "수고하셨습니다."

    return (
        f"운동을 마쳤습니다. "
        f"오늘 루틴의 {percent}퍼센트를 완료했어요. "
        f"{message} "
        "천천히 스트레칭으로 마무리 하면서 "
        "호흡을 정리하고 충분히 휴식해 주세요."
    )
