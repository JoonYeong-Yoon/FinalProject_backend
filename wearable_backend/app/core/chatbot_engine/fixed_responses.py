"""
Fixed Responses - 고정형 질문 응답 생성기 (개선 버전)
- 최신 데이터 우선 조회
- 같은 날짜 중복 제거
- 속도 유지: 각 질문당 LLM 1회 호출
"""

import json
from openai import OpenAI
import os

from app.config import (
    LLM_MODEL_MAIN,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    DEFAULT_DIFFICULTY,
    DEFAULT_DURATION,
)
from app.core.chatbot_engine.persona import get_persona_prompt
from app.core.vector_store import get_recent_summaries, search_similar_summaries
from app.core.llm_analysis import run_llm_analysis
from app.core.health_interpreter import (
    interpret_health_data,
    build_health_context_for_llm,
    calculate_health_score,
    interpret_sleep,
    interpret_heart_rate,
    interpret_activity,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_fixed_response(user_id: str, question_type: str, character: str):
    """
    고정형 질문을 처리하는 엔진 (개선 버전)

    개선 사항:
    - get_recent_summaries() 사용으로 최신 데이터 우선 조회
    - 같은 날짜 중복 자동 제거
    """

    # ✅ 디버그 로그
    print(f"\n{'='*60}")
    print(f"🤖 고정형 챗봇 요청")
    print(f"{'='*60}")
    print(f"   user_id: {user_id}")
    print(f"   question_type: {question_type}")
    print(f"   character: {character}")

    persona = get_persona_prompt(character)

    # ✅ 개선: 최신 날짜순으로 데이터 조회 (중복 제거 포함)
    print(f"\n[DEBUG] get_recent_summaries 호출 중...")
    summaries = get_recent_summaries(user_id, limit=7)
    print(f"[DEBUG] 조회 결과: {len(summaries)}개 데이터")

    if summaries:
        for i, s in enumerate(summaries[:3]):
            print(
                f"   [{i+1}] {s.get('date')} | source: {s.get('source')} | score: {s.get('health_score')}"
            )

    # summary 없을 경우 fallback
    if not summaries:
        return _get_no_data_response(character)

    # 최근 summary 데이터 추출 (가장 최신)
    recent = summaries[0]
    recent_raw = recent.get("raw", {})
    recent_summary_text = recent.get("summary_text", "")
    recent_date = recent.get("date", "최근")

    # 규칙 기반 건강 해석 (LLM 호출 없음!)
    health_interpretation = interpret_health_data(recent_raw)
    health_context = build_health_context_for_llm(recent_raw)

    # ================================
    # 1) 주간 리포트
    # ================================
    if question_type == "weekly_report":
        return _generate_weekly_report(
            persona,
            character,
            recent_raw,
            summaries,
            health_interpretation,
            health_context,
        )

    # ================================
    # 2) 오늘 운동 추천
    # ================================
    if question_type == "today_recommendation":
        return _generate_today_recommendation(
            character,
            recent_raw,
            recent_summary_text,
            summaries,
            health_interpretation,
            user_id,
        )

    # ================================
    # 3) 걸음수 (지난주)
    # ================================
    if question_type == "weekly_steps":
        return _generate_steps_report(
            persona, character, recent_raw, summaries, health_interpretation
        )

    # ================================
    # 4) 수면 분석
    # ================================
    if question_type == "sleep_report":
        return _generate_sleep_report(
            persona, character, recent_raw, summaries, health_interpretation
        )

    # ================================
    # 5) 심박수 분석
    # ================================
    if question_type == "heart_rate":
        return _generate_heart_rate_report(
            persona, character, recent_raw, health_interpretation
        )

    # ================================
    # 6) 건강 점수
    # ================================
    if question_type == "health_score":
        return _generate_health_score_report(
            persona, character, recent_raw, health_interpretation
        )

    return "⚠️ 알 수 없는 question_type 입니다."


# ============================================================
# 내부 함수들
# ============================================================


def _get_no_data_response(character: str) -> str:
    """데이터 없을 때 캐릭터별 응답"""
    responses = {
        "devil_coach": "인간, 데이터가 없잖아! 헬스커넥트 ZIP 파일을 먼저 업로드해라. 그래야 지옥 훈련을 시작할 수 있지!",
        "angel_coach": "아직 저장된 건강 데이터가 없어요 ✨ 헬스커넥트 ZIP 파일을 업로드하시면 함께 분석을 시작할 수 있답니다!",
        "booster_coach": "앗! 데이터가 없네요!! 🔥 헬스커넥트 ZIP 파일을 업로드하면 엄청난 분석을 보여드릴게요!! 렛츠고!!",
    }
    return responses.get(character, responses["booster_coach"])


def _generate_weekly_report(
    persona, character, raw, summaries, health_info, health_context
):
    """주간 건강 리포트 생성"""

    # 여러 날의 데이터 집계
    total_steps = 0
    total_calories = 0
    avg_sleep = 0
    days_count = len(summaries)

    for day in summaries[:7]:
        day_raw = day.get("raw", {})
        total_steps += day_raw.get("steps", 0)
        total_calories += day_raw.get("active_calories", 0)
        avg_sleep += day_raw.get("sleep_hr", 0)

    if days_count > 0:
        avg_sleep = avg_sleep / days_count

    # 건강 점수
    score_info = health_info.get("health_score", {})

    # 데이터 기간 표시
    if summaries:
        date_range = f"{summaries[-1].get('date', '')} ~ {summaries[0].get('date', '')}"
    else:
        date_range = "데이터 없음"

    prompt = f"""
{persona}

당신은 사용자의 이번 주 건강 리포트를 작성해야 합니다.

## 사용자 건강 데이터 요약

### 데이터 기간
{date_range}

### 최근 측정 데이터
{health_context}

### 주간 집계 (최근 {days_count}일)
• 총 걸음수: {total_steps:,}보
• 일 평균 걸음: {total_steps // max(days_count, 1):,}보
• 총 소모 칼로리: {total_calories:,}kcal
• 평균 수면: {avg_sleep:.1f}시간

### 종합 건강 점수
• 점수: {score_info.get('score', 50)}점
• 등급: {score_info.get('grade', 'C')} ({score_info.get('grade_text', '보통')})
• 평가 요소: {', '.join(score_info.get('factors', [])[:3])}

## 작성 지침
1. 캐릭터 말투를 반드시 유지하세요
2. 긍정적인 부분과 개선이 필요한 부분을 균형있게 언급하세요
3. 구체적인 숫자를 활용해 설명하세요
4. 다음 주를 위한 간단한 조언을 포함하세요
5. 3-4문단으로 자연스럽게 작성하세요 (리스트/불릿 금지)
"""

    resp = client.chat.completions.create(
        model=LLM_MODEL_MAIN,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content


def _generate_today_recommendation(
    character, raw, summary_text, summaries, health_info, user_id
):
    """오늘 운동 추천 - 템플릿 기반 (LLM 추가 호출 없음!)"""

    # LLM 분석 1회 호출
    routine = run_llm_analysis(
        summary={"raw": raw, "summary_text": summary_text},
        user_id=user_id,
        difficulty_level=DEFAULT_DIFFICULTY,
        duration_min=DEFAULT_DURATION,
    )

    analysis = routine.get("analysis", "오늘 컨디션에 맞는 루틴입니다.")
    routine_data = routine.get("ai_recommended_routine", {})
    items = routine_data.get("items", [])
    total_time = routine_data.get("total_time_min", 30)
    total_cal = routine_data.get("total_calories", 150)

    # 건강 상태 요약
    exercise_rec = health_info.get("exercise_recommendation", {})
    sleep_status = health_info.get("sleep", {}).get("level", "")

    # 캐릭터별 템플릿
    templates = {
        "devil_coach": {
            "intro": "인간, 오늘 지옥 훈련 메뉴다. 각오해라!",
            "sleep_comment": {
                "심각한 수면 부족": "수면이 부족하지만... 핑계는 안 받는다!",
                "수면 부족": "좀 피곤해 보이는군. 그래도 봐주진 않아!",
                "충분한 수면": "잘 잤군. 오늘은 제대로 굴려주지!",
                "default": "",
            },
            "outro": "이 정도는 워밍업이다. 진짜 지옥은 아직 시작도 안 했어!",
        },
        "angel_coach": {
            "intro": "오늘도 함께 건강한 하루를 만들어봐요 ✨",
            "sleep_comment": {
                "심각한 수면 부족": "수면이 부족하셨네요. 무리하지 않는 선에서 해봐요.",
                "수면 부족": "조금 피곤하실 수 있어요. 천천히 진행해요.",
                "충분한 수면": "푹 주무셨네요! 오늘 좋은 컨디션이에요.",
                "default": "",
            },
            "outro": "당신은 이미 잘 하고 있어요. 천천히, 그러나 확실하게! 💪",
        },
        "booster_coach": {
            "intro": "렛츠고오오오!! 🔥 오늘의 불꽃 루틴 시작한다!!",
            "sleep_comment": {
                "심각한 수면 부족": "수면이 부족해도 열정은 충만!! 가보자고!!",
                "수면 부족": "살짝 피곤해도 괜찮아!! 움직이면 에너지가 생겨!!",
                "충분한 수면": "컨디션 최고!! 오늘 기록 갱신 가즈아!!",
                "default": "",
            },
            "outro": "파워! 파워! 파워! 오늘도 완전 찢었다!! 🎉",
        },
    }

    template = templates.get(character, templates["booster_coach"])
    sleep_comment = template["sleep_comment"].get(
        sleep_status, template["sleep_comment"]["default"]
    )

    # 운동 목록 포맷팅
    exercise_lines = []
    for i, item in enumerate(items, 1):
        name = item.get("exercise_name", "운동")
        duration = item.get("duration_sec", 30)
        sets = item.get("set_count", 3)
        rest = item.get("rest_sec", 10)
        met = item.get("met", 4)
        exercise_lines.append(
            f"  {i}. {name} - {duration}초 x {sets}세트 (휴식 {rest}초) [MET {met}]"
        )

    exercises_text = (
        "\n".join(exercise_lines) if exercise_lines else "  - 기본 스트레칭 루틴"
    )

    # 최종 응답 조합
    response_parts = [template["intro"]]

    if sleep_comment:
        response_parts.append(f"\n{sleep_comment}")

    response_parts.append(
        f"""

📊 오늘의 분석: {analysis}

⏱️ 총 운동 시간: {total_time}분
🔥 예상 소모 칼로리: {total_cal}kcal
💪 권장 강도: {exercise_rec.get('recommended_level', '중')}

🏋️ 추천 운동:
{exercises_text}

{template['outro']}"""
    )

    return "".join(response_parts)


def _generate_steps_report(persona, character, raw, summaries, health_info):
    """걸음수 분석 리포트"""

    # 여러 날의 걸음수 집계
    steps_data = []
    for day in summaries[:7]:
        day_raw = day.get("raw", {})
        steps_data.append(
            {
                "date": day.get("date", ""),
                "steps": day_raw.get("steps", 0),
                "distance": day_raw.get("distance_km", 0),
            }
        )

    total_steps = sum(d["steps"] for d in steps_data)
    avg_steps = total_steps // max(len(steps_data), 1)
    total_distance = sum(d["distance"] for d in steps_data)

    activity_info = health_info.get("activity", {})

    prompt = f"""
{persona}

사용자의 지난주 걸음수 데이터를 분석해주세요.

## 걸음수 데이터

### 최근 {len(steps_data)}일 기록
{json.dumps(steps_data, ensure_ascii=False, indent=2)}

### 집계
• 총 걸음수: {total_steps:,}보
• 일 평균: {avg_steps:,}보
• 총 이동거리: {total_distance:.2f}km

### 활동량 평가
• 활동 레벨: {activity_info.get('activity_level', 'unknown')}
• 분석: {activity_info.get('message', '')}
• 권장사항: {activity_info.get('recommendation', '')}

## 작성 지침
1. 캐릭터 말투 유지
2. 목표 대비 달성률 언급 (일반 목표: 7,000~10,000보/일)
3. 가장 많이 걸은 날과 적게 걸은 날 언급
4. 개선을 위한 구체적 조언
5. 2-3문단으로 자연스럽게 (리스트 금지)
"""

    resp = client.chat.completions.create(
        model=LLM_MODEL_MAIN,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content


def _generate_sleep_report(persona, character, raw, summaries, health_info):
    """수면 분석 리포트"""

    # 여러 날의 수면 데이터 집계
    sleep_data = []
    for day in summaries[:7]:
        day_raw = day.get("raw", {})
        sleep_data.append(
            {
                "date": day.get("date", ""),
                "sleep_hr": round(day_raw.get("sleep_hr", 0), 1),
                "sleep_min": int(day_raw.get("sleep_min", 0)),
            }
        )

    valid_sleep = [d for d in sleep_data if d["sleep_hr"] > 0]
    avg_sleep = sum(d["sleep_hr"] for d in valid_sleep) / max(len(valid_sleep), 1)

    sleep_info = health_info.get("sleep", {})

    prompt = f"""
{persona}

사용자의 수면 패턴을 분석해주세요.

## 수면 데이터

### 최근 수면 기록
{json.dumps(sleep_data, ensure_ascii=False, indent=2)}

### 집계
• 평균 수면: {avg_sleep:.1f}시간
• 유효 기록 일수: {len(valid_sleep)}일

### 수면 상태 분석
• 상태: {sleep_info.get('status', 'unknown')}
• 수준: {sleep_info.get('level', '')}
• 분석: {sleep_info.get('message', '')}
• 권장사항: {sleep_info.get('recommendation', '')}
• 운동 영향: {sleep_info.get('exercise_impact', '')}

## 작성 지침
1. 캐릭터 말투 유지
2. 권장 수면 시간(7-9시간) 대비 평가
3. 수면 패턴의 일관성 평가
4. 수면 개선을 위한 구체적 조언
5. 2-3문단으로 자연스럽게 (리스트 금지)
"""

    resp = client.chat.completions.create(
        model=LLM_MODEL_MAIN,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content


def _generate_heart_rate_report(persona, character, raw, health_info):
    """심박수 분석 리포트"""

    hr_info = health_info.get("heart_rate", {})

    prompt = f"""
{persona}

사용자의 심박수 데이터를 분석해주세요.

## 심박수 데이터
• 평균 심박수: {raw.get('heart_rate', 0)}bpm
• 휴식기 심박수: {raw.get('resting_heart_rate', 0)}bpm
• 걷기 심박수: {raw.get('walking_heart_rate', 0)}bpm
• 심박변이도(HRV): {raw.get('hrv', 0)}ms

## 심박수 분석
• 피트니스 레벨: {hr_info.get('fitness_level', 'unknown')}
• 분석: {hr_info.get('message', '')}
• 운동 권장: {hr_info.get('exercise_impact', '')}

## 참고 기준
• 운동선수: 휴식기 심박수 50bpm 미만
• 매우 건강: 50-60bpm
• 양호: 60-70bpm
• 평균: 70-80bpm
• 개선 필요: 80bpm 이상

## 작성 지침
1. 캐릭터 말투 유지
2. 현재 심폐 기능 수준 평가
3. 휴식기 심박수의 의미 설명
4. 심폐 기능 개선을 위한 조언
5. 2-3문단으로 자연스럽게 (리스트 금지)
"""

    resp = client.chat.completions.create(
        model=LLM_MODEL_MAIN,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content


def _generate_health_score_report(persona, character, raw, health_info):
    """건강 점수 리포트 - 규칙 기반 점수 + LLM 해석"""

    score_info = health_info.get("health_score", {})
    score = score_info.get("score", 50)
    grade = score_info.get("grade", "C")
    grade_text = score_info.get("grade_text", "보통")
    factors = score_info.get("factors", [])

    # 각 영역별 상태
    sleep_info = health_info.get("sleep", {})
    activity_info = health_info.get("activity", {})
    hr_info = health_info.get("heart_rate", {})
    bmi_info = health_info.get("bmi", {})

    prompt = f"""
{persona}

사용자의 종합 건강 점수를 설명해주세요.

## 종합 건강 점수
🏅 **{score}점 / 100점** ({grade}등급 - {grade_text})

## 점수 산정 요소
{chr(10).join(f'• {f}' for f in factors)}

## 영역별 상태
• 수면: {sleep_info.get('level', '데이터 없음')} - {sleep_info.get('message', '')}
• 활동량: {activity_info.get('activity_level', '데이터 없음')} - {activity_info.get('message', '')}
• 심박수: {hr_info.get('fitness_level', '데이터 없음')} - {hr_info.get('message', '')}
• 체형: {bmi_info.get('category', '데이터 없음')} - {bmi_info.get('message', '')}

## 상세 데이터
• 수면: {raw.get('sleep_hr', 0):.1f}시간
• 걸음수: {raw.get('steps', 0):,}보
• 심박수: {raw.get('heart_rate', 0)}bpm / 휴식기 {raw.get('resting_heart_rate', 0)}bpm
• BMI: {raw.get('bmi', 0):.1f}

## 작성 지침
1. 캐릭터 말투 유지
2. 점수와 등급의 의미 설명
3. 강점 영역 칭찬
4. 개선이 필요한 영역 조언
5. 점수 향상을 위한 구체적 목표 제시
6. 3-4문단으로 자연스럽게 (리스트 금지)
"""

    resp = client.chat.completions.create(
        model=LLM_MODEL_MAIN,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content
