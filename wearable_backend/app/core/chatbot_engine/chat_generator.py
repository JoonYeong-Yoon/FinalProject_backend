"""
Chat Generator - 개선 버전
- 기본: 최신 데이터 기반 응답
- 시간 표현 감지: 해당 날짜/기간 데이터 사용
- 비교/패턴 키워드: 의미 유사도 검색 활용
"""

import os
import json
from openai import OpenAI

from app.core.chatbot_engine.intent_classifier import classify_intent
from app.core.chatbot_engine.persona import get_persona_prompt
from app.core.chatbot_engine.rag_query import query_health_data
from app.core.llm_analysis import run_llm_analysis
from app.core.health_interpreter import (
    interpret_health_data,
    build_health_context_for_llm,
)
from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE

# ✅ 챗봇 응답용 토큰 제한 (간결화)
CHAT_MAX_TOKENS = 400


class ChatGenerator:

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ================================================================
    # 1) OpenAI 호출
    # ================================================================
    def _call_openai(
        self, system_prompt: str, user_prompt: str, max_tokens: int = None
    ):
        resp = self.client.chat.completions.create(
            model=LLM_MODEL_MAIN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=max_tokens or CHAT_MAX_TOKENS,
        )
        return resp.choices[0].message.content

    # ================================================================
    # 2) System Prompt 생성
    # ================================================================
    def _build_system_prompt(self, persona_prompt: str, context_type: str) -> str:
        """간결한 시스템 프롬프트 생성"""

        base_instructions = f"""당신은 아래 캐릭터입니다:

{persona_prompt}

## 핵심 규칙
1. 캐릭터 말투 유지
2. **반드시 2-3문장으로 간결하게 응답**
3. 핵심만 전달, 불필요한 설명 생략
4. 리스트/불릿 사용 금지
"""

        if context_type == "health_query":
            base_instructions += """
## 건강 질문 응답
- 핵심 수치 1-2개만 언급
- 짧은 조언 1개 추가
"""
        elif context_type == "routine_request":
            base_instructions += """
## 운동 루틴 응답
- 운동 목록은 별도 포맷으로 제공됨
- 간단한 격려만 추가
"""
        elif context_type == "comparison":
            base_instructions += """
## 비교/패턴 분석 응답
- 여러 날짜 데이터 비교 시 핵심 차이점만 언급
- 트렌드가 있으면 간단히 설명
"""
        else:
            base_instructions += """
## 일반 대화
- 친근하게 1-2문장으로 응답
"""

        return base_instructions

    # ================================================================
    # 3) 데이터 컨텍스트 포맷팅
    # ================================================================
    def _format_data_context(self, rag_result: dict, message: str) -> str:
        """RAG 결과를 LLM 컨텍스트로 포맷팅"""
        similar = rag_result.get("similar_days", [])
        mode = rag_result.get("mode", "unknown")

        if not similar:
            return "데이터 없음"

        # 단일 데이터 (최신 or 특정 날짜)
        if len(similar) == 1:
            item = similar[0]
            raw = item.get("raw", {})
            date = item.get("date", "")
            health_context = build_health_context_for_llm(raw)
            return f"[{date} 데이터]\n{health_context}"

        # 복수 데이터 (범위 or 유사도)
        context_parts = []
        for item in similar[:5]:  # 최대 5개
            raw = item.get("raw", {})
            date = item.get("date", "")

            # 간략한 요약
            sleep = raw.get("sleep_hr", 0)
            steps = raw.get("steps", 0)
            score = item.get("health_score", 0)

            summary = (
                f"[{date}] 수면 {sleep:.1f}h, 걸음 {steps:,}보, 건강점수 {score}점"
            )
            context_parts.append(summary)

        return "\n".join(context_parts)

    # ================================================================
    # 4) 운동 루틴 템플릿 응답
    # ================================================================
    def _format_routine_response(
        self, character: str, analysis: str, routine_data: dict, health_info: dict
    ) -> str:
        """간결한 운동 루틴 응답"""
        items = routine_data.get("items", [])
        total_time = routine_data.get("total_time_min", 30)
        total_cal = routine_data.get("total_calories", 150)

        exercise_rec = health_info.get("exercise_recommendation", {})

        # ========== 5가지 전문 캐릭터 + 레거시 캐릭터 인트로/아웃트로 ==========
        intros = {
            # 새로운 5가지 전문 캐릭터
            "default": "오늘의 맞춤 루틴이에요! 💪",
            "trainer": "자, 오늘 근육 파괴 메뉴다! 🏋️",
            "yoga": "오늘의 수련을 시작해볼까요? 🧘",
            "cardio": "심박수 올리러 가볼까요?! 🏃",
            "diet": "오늘의 운동 + 영양 가이드예요! 🥗",
            # 레거시 캐릭터
            "devil_coach": "인간, 오늘 메뉴다!",
            "angel_coach": "오늘의 루틴이에요 ✨",
            "booster_coach": "렛츠고!! 🔥",
        }

        outros = {
            # 새로운 5가지 전문 캐릭터
            "default": "자세에 집중하며 진행해봐요! 화이팅! 💪",
            "trainer": "끝나면 단백질 30g 섭취 잊지 마! 💪",
            "yoga": "호흡에 집중하며 천천히. 나마스테 🙏",
            "cardio": "쿨다운 5분 잊지 마세요! 🔥",
            "diet": "운동 후 30분 내 단백질 섭취! 🍗",
            # 레거시 캐릭터
            "devil_coach": "각오해라!",
            "angel_coach": "화이팅! 💪",
            "booster_coach": "파워!! 🎉",
        }

        intro = intros.get(character, intros["default"])
        outro = outros.get(character, outros["default"])

        # 운동 목록 (간소화)
        exercise_lines = []
        for i, item in enumerate(items[:5], 1):  # 최대 5개
            name = item.get("exercise_name", "운동")
            duration = item.get("duration_sec", 30)
            sets = item.get("set_count", 3)
            exercise_lines.append(f"{i}. {name} {duration}초×{sets}세트")

        exercises_text = "\n".join(exercise_lines) if exercise_lines else "- 스트레칭"

        return f"""{intro}

⏱️ {total_time}분 | 🔥 {total_cal}kcal | 💪 {exercise_rec.get('recommended_level', '중')}

{exercises_text}

{outro}"""

    # ================================================================
    # 5) 메인 generate() - 개선 버전
    # ================================================================
    def generate(self, user_id: str, message: str, character: str):

        # ✅ 개선된 intent 분류 (시간/비교 컨텍스트 포함)
        intent_result = classify_intent(message)
        intent = intent_result["intent"]
        time_context = intent_result.get("time_context")
        use_similarity = intent_result.get("use_similarity", False)

        persona_prompt = get_persona_prompt(character)

        # ================================================================
        # 1) 건강 데이터 질문 (health_query)
        # ================================================================
        if intent == "health_query":

            # ✅ 개선: intent_result 전달하여 적절한 데이터 조회
            rag = query_health_data(message, user_id, intent_result=intent_result)
            similar = rag.get("similar_days", [])
            mode = rag.get("mode", "latest")

            if not similar:
                system = self._build_system_prompt(persona_prompt, "health_query")
                user_prompt = f"""질문: {message}

데이터 없음. 일반 조언을 2문장으로."""
                return self._call_openai(system, user_prompt, max_tokens=200)

            # 데이터 컨텍스트 생성
            data_context = self._format_data_context(rag, message)

            # 비교/패턴 모드면 다른 프롬프트
            if use_similarity and len(similar) > 1:
                system = self._build_system_prompt(persona_prompt, "comparison")
                user_prompt = f"""질문: {message}

{data_context}

**여러 날짜 데이터를 비교하여 2-3문장으로 핵심만 답변하세요.**"""
            else:
                # 단일 데이터 (최신 or 특정 날짜)
                top_raw = similar[0]["raw"]
                health_context = build_health_context_for_llm(top_raw)
                date_info = similar[0].get("date", "")

                system = self._build_system_prompt(persona_prompt, "health_query")

                # 시간 표현이 있었으면 날짜 명시
                if time_context:
                    user_prompt = f"""질문: {message}

[{date_info} 데이터]
{health_context}

**2-3문장으로 핵심만 답변하세요.**"""
                else:
                    user_prompt = f"""질문: {message}

[최신 데이터: {date_info}]
{health_context}

**2-3문장으로 핵심만 답변하세요.**"""

            return self._call_openai(system, user_prompt, max_tokens=300)

        # ================================================================
        # 2) 운동 루틴 요청 (routine_request)
        # ================================================================
        if intent == "routine_request":

            # ✅ 루틴 요청은 항상 최신 데이터 사용
            rag = query_health_data(
                message,
                user_id,
                intent_result={
                    "intent": "routine_request",
                    "time_context": None,
                    "use_similarity": False,
                },
            )
            similar = rag.get("similar_days", [])

            if not similar:
                system = self._build_system_prompt(persona_prompt, "routine_request")
                user_prompt = f"""요청: {message}

데이터 없음. 기본 홈트 루틴을 2문장으로 설명."""
                return self._call_openai(system, user_prompt, max_tokens=200)

            top_raw = similar[0]["raw"]
            health_interpretation = interpret_health_data(top_raw)

            routine_result = run_llm_analysis(
                summary={
                    "raw": top_raw,
                    "summary_text": similar[0].get("summary_text", ""),
                },
                rag_result={"similar_days": similar},
                difficulty_level="중",
                duration_min=30,
            )

            analysis_text = routine_result.get(
                "analysis", "오늘 컨디션에 맞는 루틴입니다."
            )
            routine_data = routine_result.get("ai_recommended_routine", {})

            return self._format_routine_response(
                character, analysis_text, routine_data, health_interpretation
            )

        # ================================================================
        # 3) 일반 대화
        # ================================================================
        system = self._build_system_prompt(persona_prompt, "general")
        user_prompt = f"""메시지: {message}

**1-2문장으로 짧게 응답.**"""
        return self._call_openai(system, user_prompt, max_tokens=150)
