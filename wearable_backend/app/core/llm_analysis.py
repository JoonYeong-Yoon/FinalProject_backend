import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE, LLM_MAX_TOKENS
from app.core.rag_query import (
    build_rag_query,
    classify_rag_strength,
)
from app.core.vector_store import search_similar_summaries
from app.core.health_interpreter import (
    interpret_health_data,
    build_health_context_for_llm,
    build_analysis_text,
    analyze_rag_patterns,
    recommend_exercise_intensity,
    calculate_health_score,
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================================
# 1) 유틸 함수들
# ==========================================================
def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return text


def try_parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


# ==========================================================
# 2) 데이터 품질 확인
# ==========================================================
def check_data_quality(raw: dict) -> bool:
    """최소 데이터 품질 확인 - 수면 OR 활동량 중 하나는 있어야 함"""
    has_sleep = raw.get("sleep_hr", 0) > 0
    has_activity = raw.get("steps", 0) > 0
    return has_sleep or has_activity


# ==========================================================
# 3) LLM 결과 검증
# ==========================================================
def validate_routine(result: dict, difficulty: str, target_min: int) -> bool:
    """LLM 결과 검증 - 시간, MET 범위 확인"""
    try:
        routine = result.get("ai_recommended_routine", {})
        items = routine.get("items", [])

        if not items:
            print("[WARN] 검증 실패: items 비어있음")
            return False

        # 1) 시간 검증 (±20% 허용)
        total_sec = 0
        for item in items:
            duration = item.get("duration_sec", 30)
            sets = item.get("set_count", 3)
            rest = item.get("rest_sec", 15)
            total_sec += (duration * sets) + (rest * (sets - 1))

        target_sec = target_min * 60
        if not (target_sec * 0.8 <= total_sec <= target_sec * 1.2):
            print(f"[WARN] 검증 실패: 시간 {total_sec}초 (목표 {target_sec}±20%)")
            return False

        # 2) MET 범위 검증
        met_ranges = {"하": (2.5, 4.5), "중": (3.5, 5.5), "상": (4.5, 9.0)}
        min_met, max_met = met_ranges.get(difficulty, (3.5, 5.5))

        for item in items:
            item_met = item.get("met", 0)
            if not (min_met <= item_met <= max_met):
                print(f"[WARN] 검증 실패: MET {item_met} (범위 {min_met}-{max_met})")
                return False

        return True

    except Exception as e:
        print(f"[ERROR] 검증 중 오류: {str(e)}")
        return False


# ==========================================================
# 4) 상세 건강 리포트 생성
# ==========================================================
def build_detailed_health_analysis(raw: dict) -> str:
    """상세한 건강 상태 분석 텍스트 생성"""

    interpretation = interpret_health_data(raw)
    lines = []

    score_info = interpretation["health_score"]
    lines.append("=" * 50)
    lines.append("📊 종합 건강 분석 리포트")
    lines.append("=" * 50)
    lines.append(f"\n🏅 건강 점수: {score_info['score']}점 / 100점")
    lines.append(f"   등급: {score_info['grade']} ({score_info['grade_text']})")
    if score_info.get("factors"):
        lines.append("   산정 요소:")
        for factor in score_info["factors"]:
            lines.append(f"     • {factor}")

    sleep = interpretation["sleep"]
    lines.append(f"\n😴 수면 분석")
    lines.append(f"   상태: {sleep.get('level', '데이터 없음')}")
    lines.append(f"   수면 시간: {raw.get('sleep_hr', 0)}시간")
    if sleep.get("message"):
        lines.append(f"   평가: {sleep['message']}")

    activity = interpretation["activity"]
    lines.append(f"\n🚶 활동량 분석")
    lines.append(f"   걸음수: {raw.get('steps', 0):,}보")
    lines.append(f"   활동 레벨: {activity.get('activity_level', 'unknown')}")
    if activity.get("message"):
        lines.append(f"   평가: {activity['message']}")

    hr = interpretation["heart_rate"]
    lines.append(f"\n❤️ 심박수 분석")
    lines.append(f"   휴식기 심박수: {raw.get('resting_heart_rate', 0)}bpm")
    lines.append(f"   피트니스 레벨: {hr.get('fitness_level', 'unknown')}")

    exercise_rec = interpretation["exercise_recommendation"]
    lines.append(f"\n💪 권장 운동 강도: {exercise_rec.get('recommended_level', '중')}")

    lines.append("\n" + "=" * 50)

    return "\n".join(lines)


# ==========================================================
# 5) 개선된 Fallback 루틴 (10분/30분/60분 모두 지원)
# ==========================================================
def get_fallback_routine(
    difficulty_level: str, duration_min: int, raw: dict = None
) -> dict:
    """
    개선된 Fallback 루틴
    - 모든 시간대 지원 (10분/30분/60분)
    - 동적 운동 선택 (순환 반복)
    - 상세 분석 텍스트 포함
    """

    # ============================================
    # 난이도별 운동 풀 (MET 범위 엄격 준수)
    # ============================================
    exercise_pools = {
        "하": [
            {
                "exercise_name": "standing knee up",
                "category": [1, 3],
                "difficulty": 3,
                "met": 3.8,
            },
            {
                "exercise_name": "hip thrust",
                "category": [3, 2],
                "difficulty": 3,
                "met": 3.5,
            },
            {
                "exercise_name": "standing side crunch",
                "category": [2, 3],
                "difficulty": 3,
                "met": 4.0,
            },
            {
                "exercise_name": "cross lunge",
                "category": [3, 2],
                "difficulty": 4,
                "met": 3.8,
            },
        ],
        "중": [
            {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
            {
                "exercise_name": "step forward dynamic lunge",
                "category": [3],
                "difficulty": 4,
                "met": 4.0,
            },
            {
                "exercise_name": "lying leg raise",
                "category": [3, 2],
                "difficulty": 4,
                "met": 4.0,
            },
            {
                "exercise_name": "scissor cross",
                "category": [2, 3],
                "difficulty": 4,
                "met": 4.5,
            },
            {
                "exercise_name": "Y-exercise",
                "category": [1, 2],
                "difficulty": 3,
                "met": 4.5,
            },
            {
                "exercise_name": "knee push up",
                "category": [1, 2],
                "difficulty": 3,
                "met": 5.0,
            },
        ],
        "상": [
            {
                "exercise_name": "burpee test",
                "category": [4],
                "difficulty": 5,
                "met": 8.0,
            },
            {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
            {
                "exercise_name": "push up",
                "category": [1, 2],
                "difficulty": 4,
                "met": 6.0,
            },
            {
                "exercise_name": "bicycle crunch",
                "category": [3, 2],
                "difficulty": 5,
                "met": 5.0,
            },
            {
                "exercise_name": "side lunge",
                "category": [3],
                "difficulty": 5,
                "met": 5.0,
            },
            {
                "exercise_name": "good morning exercise",
                "category": [3],
                "difficulty": 5,
                "met": 5.0,
            },
        ],
    }

    # ============================================
    # 시간대별 설정
    # ============================================
    target_seconds = duration_min * 60
    pool = exercise_pools.get(difficulty_level, exercise_pools["중"])

    if duration_min <= 15:
        base_sets, max_sets = 2, 3
        rest_sec = 10 if difficulty_level != "하" else 15
        duration_sec = 30
    elif duration_min <= 30:
        base_sets, max_sets = 3, 4
        rest_sec = 10 if difficulty_level != "하" else 15
        duration_sec = 40
    else:  # 60분
        base_sets, max_sets = 3, 5
        rest_sec = 15
        duration_sec = 45

    # ============================================
    # 운동 항목 생성 (순환 반복)
    # ============================================
    items = []
    total_sec = 0
    idx = 0

    while total_sec < target_seconds * 0.8:
        ex = pool[idx % len(pool)]
        sets = base_sets

        item_time = (duration_sec * sets) + (rest_sec * (sets - 1))

        if total_sec + item_time > target_seconds * 1.2:
            break

        items.append(
            {
                "exercise_name": ex["exercise_name"],
                "category": ex["category"],
                "difficulty": ex["difficulty"],
                "met": ex["met"],
                "duration_sec": duration_sec,
                "rest_sec": rest_sec,
                "set_count": sets,
                "reps": None,
            }
        )

        total_sec += item_time
        idx += 1

    # ============================================
    # 칼로리 계산
    # ============================================
    avg_met = sum(item["met"] for item in items) / max(len(items), 1)
    total_calories = int(avg_met * 3.5 * 70 / 200 * (total_sec / 60))

    # ============================================
    # 분석 텍스트 생성
    # ============================================
    if raw:
        analysis = build_analysis_text(
            raw=raw,
            difficulty_level=difficulty_level,
            duration_min=duration_min,
            item_count=len(items),
            total_time_sec=total_sec,
        )
    else:
        analysis = f"안전 모드로 {difficulty_level} 난이도 운동 루틴을 생성했습니다."

    return {
        "analysis": analysis,
        "ai_recommended_routine": {
            "total_time_min": duration_min,
            "total_calories": total_calories,
            "items": items,
        },
        "used_data_ranked": {
            "primary": "fallback_routine",
            "secondary": "rule_based",
        },
    }


# ==========================================================
# 6) SEED_JSON (17종 운동 목록)
# ==========================================================
SEED_JSON = """
[
  {"exercise_name": "standing side crunch", "category": [2, 3], "difficulty": 3, "met": 4.0},
  {"exercise_name": "standing knee up", "category": [1, 3], "difficulty": 3, "met": 3.8},
  {"exercise_name": "burpee test", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "step forward dynamic lunge", "category": [3], "difficulty": 4, "met": 4.0},
  {"exercise_name": "side lunge", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "cross lunge", "category": [3, 2], "difficulty": 4, "met": 3.8},
  {"exercise_name": "good morning exercise", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "lying leg raise", "category": [3, 2], "difficulty": 4, "met": 4.0},
  {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
  {"exercise_name": "bicycle crunch", "category": [3, 2], "difficulty": 5, "met": 5.0},
  {"exercise_name": "scissor cross", "category": [2, 3], "difficulty": 4, "met": 4.5},
  {"exercise_name": "hip thrust", "category": [3, 2], "difficulty": 3, "met": 3.5},
  {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "push up", "category": [1, 2], "difficulty": 4, "met": 6.0},
  {"exercise_name": "knee push up", "category": [1, 2], "difficulty": 3, "met": 5.0},
  {"exercise_name": "Y-exercise", "category": [1, 2], "difficulty": 3, "met": 4.5}
]
"""


# ==========================================================
# 7) 메인 LLM 분석 함수 (Option C)
# ==========================================================
def run_llm_analysis(
    summary: dict,
    user_id: str,
    difficulty_level: str,
    duration_min: int,
) -> dict:
    """
    LLM 기반 운동 분석 엔진 - Option C

    1) 강제 Fallback 조건: 강도 "하" / 점수 < 50 / 데이터 부족
    2) LLM 호출 후 검증
    3) 검증 실패 시 Fallback
    """

    raw = summary.get("raw", {})

    # RAG 검색
    rag_query = build_rag_query(raw)

    rag_result = search_similar_summaries(
        query_dict=rag_query,
        user_id=user_id,
        top_k=3,
    )

    similar_days = rag_result.get("similar_days", [])

    # 규칙 기반 건강 해석
    health_context = build_health_context_for_llm(raw)
    exercise_rec = recommend_exercise_intensity(raw)
    health_score = calculate_health_score(raw)

    auto_difficulty = exercise_rec.get("recommended_level", difficulty_level)
    score = health_score.get("score", 50)

    rag_strength = classify_rag_strength(similar_days)

    if rag_strength == "none":
        rag_context = ""
    elif rag_strength == "weak":
        rag_context = (
            "📚 과거에 유사한 기록이 일부 있었으나, " "참고 수준으로만 반영했습니다."
        )
    else:  # strong
        rag_context = analyze_rag_patterns(similar_days)

    # ============================================
    # 1) 강제 Fallback 조건
    # ============================================
    use_fallback = False
    fallback_reason = ""

    if auto_difficulty == "하":
        use_fallback = True
        fallback_reason = f"권장 강도 '하' (안전 모드)"
    elif score < 50:
        use_fallback = True
        fallback_reason = f"건강 점수 {score}점 (50점 미만)"
    elif not check_data_quality(raw):
        use_fallback = True
        fallback_reason = "데이터 부족 (수면/활동량 없음)"

    if use_fallback:
        print(f"[INFO] Fallback 사용: {fallback_reason}")
        result = get_fallback_routine(auto_difficulty, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score,
            "recommended_intensity": auto_difficulty,
            "fallback_reason": fallback_reason,
        }
        return result

    # ============================================
    # 2) LLM 호출
    # ============================================
    detailed_report = build_detailed_health_analysis(raw)

    raw_block = f"""[사용자 건강 데이터]

📊 건강 점수: {score}점 ({health_score.get('grade', 'C')}등급)

• 수면: {raw.get('sleep_hr', 0)}시간
• 걸음수: {raw.get('steps', 0):,}보
• 활동 칼로리: {raw.get('active_calories', 0)}kcal
• 심박수: {raw.get('heart_rate', 0)}bpm / 휴식기 {raw.get('resting_heart_rate', 0)}bpm
• BMI: {raw.get('bmi', 0):.1f}"""

    system_prompt = f"""당신은 피트니스 코치입니다.

## 참고 정보
- RAG 상태: {rag_strength}
  * none  → 과거 데이터 참고 금지
  * weak  → 참고 멘트 수준
  * strong → 반복 패턴 반영 가능

### RAG 상태별 analysis 톤 가이드

[RAG none]
- 오늘 하루 기준의 건강 상태 분석에 집중한다.
- 과거 기록이나 누적 경향에 대한 언급은 하지 않는다.

[RAG weak]
- 최근 기록을 참고하되, 단정적인 표현은 피한다.
- "가능성", "경향", "참고 수준"의 표현을 사용한다.

[RAG strong]
- 반복적으로 관찰된 생활 패턴을 반영한다.
- 변화 방향 판단은 반드시
  "수면 / 활동량 / 회복 지표" 중 하나 이상을 근거로 한다.
- analysis에는 반드시 다음과 같은 누적 관점 표현 중 하나 이상을 포함한다:
  • "최근 전반적으로"
  • "반복적으로 나타나는 경향"
  • "일시적이라기보다는 습관적 요인"

- 각 운동 선택 이유는 반드시 다음 중 하나에 근거해야 한다:
  1) 과거 기록에서 반복적으로 부족했던 요소
  2) 최근 개선이 필요하다고 판단된 지표

- 주의사항은 반드시 다음 중 하나를 포함해야 한다:
  1) 과거 기록에서 반복된 위험 신호
  2) 최근 회복 지표가 낮았던 항목

- analysis는 반드시 다음을 모두 포함해야 한다:
  1) 과거 기록과 비교한 변화 방향
     (개선 / 유지 / 악화 중 하나 명시)
  2) 오늘 운동 강도를 그 변화에 맞춘 이유
  3) 반복 패턴이 있다면
     "지속 필요" 또는 "조정 필요" 중 하나를 명확히 명시
      
## 역할
건강 데이터를 분석하여 맞춤형 운동 루틴을 JSON으로 처방합니다.

## 규칙

### 1. analysis 작성 (3-4문장)
- 현재 건강 상태 평가
- 운동 선택 이유
- 주의사항

### 2. 운동 선택 (MET 범위 엄격 준수!)
- 17종 운동 목록에서만 선택
- 시스템 권장 강도: {auto_difficulty}
  * 하: MET 2.5-4
  * 중: MET 4-5
  * 상: MET 5-8

### 3. 시간 계산 (매우 중요!)
- 목표: {duration_min}분 = {duration_min * 60}초
- 각 운동: (duration_sec × set_count) + (rest_sec × (set_count - 1))
- 모든 운동 합계가 목표의 80~120% 이내

## 응답 JSON
{{
  "analysis": "3-4문장 분석",
  "ai_recommended_routine": {{
    "total_time_min": {duration_min},
    "total_calories": 예상칼로리,
    "items": [
      {{
        "exercise_name": "운동명",
        "category": [카테고리],
        "difficulty": 난이도,
        "met": MET값,
        "duration_sec": 30-60,
        "rest_sec": 10-20,
        "set_count": 2-5,
        "reps": null
      }}
    ]
  }},
  "used_data_ranked": {{
    "primary": "주요 데이터",
    "secondary": "보조 데이터"
  }}
}}"""

    user_prompt = f"""{raw_block}

{health_context}

{rag_context}

---
• 요청 난이도: {difficulty_level}
• 시스템 권장: {auto_difficulty} (반드시 준수!)
• 목표 시간: {duration_min}분

## 운동 목록
{SEED_JSON}

JSON만 출력. 시간 계산 정확히!"""

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_MAIN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=LLM_MAX_TOKENS,  # ✅ config.py의 설정값 사용
            temperature=LLM_TEMPERATURE,  # ✅ config.py의 설정값 사용
        )

        raw_text = resp.choices[0].message.content
        cleaned = clean_json_text(raw_text)
        parsed = try_parse_json(cleaned)

        # ============================================
        # 3) LLM 결과 검증
        # ============================================
        if parsed and "analysis" in parsed and "ai_recommended_routine" in parsed:
            if validate_routine(parsed, auto_difficulty, duration_min):
                parsed["detailed_health_report"] = detailed_report
                parsed["health_context"] = {
                    "health_score": health_score,
                    "recommended_intensity": auto_difficulty,
                    "llm_validated": True,
                }
                print(f"[INFO] LLM 결과 검증 성공")
                return parsed
            else:
                print(f"[WARN] LLM 결과 검증 실패 → Fallback 사용")
                result = get_fallback_routine(auto_difficulty, duration_min, raw)
                result["health_context"] = {
                    "health_score": health_score,
                    "recommended_intensity": auto_difficulty,
                    "fallback_reason": "LLM 결과 검증 실패",
                }
                return result

        print(f"[WARN] LLM JSON 파싱 실패 → Fallback 사용")
        result = get_fallback_routine(auto_difficulty, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score,
            "recommended_intensity": auto_difficulty,
            "fallback_reason": "LLM JSON 파싱 실패",
        }
        return result

    except Exception as e:
        print(f"[ERROR] LLM 호출 실패: {str(e)} → Fallback 사용")
        result = get_fallback_routine(auto_difficulty, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score,
            "recommended_intensity": auto_difficulty,
            "fallback_reason": f"LLM 호출 오류: {str(e)}",
        }
        return result


# ==========================================================
# 8) 헬퍼 함수들
# ==========================================================
def get_health_analysis_context(raw: dict) -> str:
    return build_health_context_for_llm(raw)


def get_health_score(raw: dict) -> dict:
    return calculate_health_score(raw)


def get_detailed_health_report(raw: dict) -> str:
    return build_detailed_health_analysis(raw)
