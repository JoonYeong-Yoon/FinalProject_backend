"""
Chat Generator - 자유형 챗봇 응답 생성기 (간결화 버전)
응답 길이: 기존 대비 약 50% 축소
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
CHAT_MAX_TOKENS = 400  # 기존 2048 → 400으로 축소


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
    # 2) System Prompt 생성 (간결화)
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
        else:
            base_instructions += """
## 일반 대화
- 친근하게 1-2문장으로 응답
"""

        return base_instructions

    # ================================================================
    # 3) RAG 데이터 포맷팅 (간소화)
    # ================================================================
    def _format_rag_brief(self, rag: dict) -> str:
        """RAG 결과 간소화"""
        similar = rag.get("similar_days", [])
        if not similar:
            return ""

        # 최근 1개만 간략히
        item = similar[0]
        raw = item.get("raw", {})
        return (
            f"유사패턴: 수면 {raw.get('sleep_hr', 0)}h, 걸음 {raw.get('steps', 0):,}보"
        )

    # ================================================================
    # 4) 운동 루틴 템플릿 응답 (간소화)
    # ================================================================
    def _format_routine_response(
        self, character: str, analysis: str, routine_data: dict, health_info: dict
    ) -> str:
        """간결한 운동 루틴 응답"""
        items = routine_data.get("items", [])
        total_time = routine_data.get("total_time_min", 30)
        total_cal = routine_data.get("total_calories", 150)

        exercise_rec = health_info.get("exercise_recommendation", {})

        # 캐릭터별 한줄 인트로
        intros = {
            "devil_coach": "인간, 오늘 메뉴다!",
            "angel_coach": "오늘의 루틴이에요 ✨",
            "booster_coach": "렛츠고!! 🔥",
        }

        outros = {
            "devil_coach": "각오해라!",
            "angel_coach": "화이팅! 💪",
            "booster_coach": "파워!! 🎉",
        }

        intro = intros.get(character, intros["booster_coach"])
        outro = outros.get(character, outros["booster_coach"])

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
    # 5) 메인 generate() - 간결화
    # ================================================================
    def generate(self, user_id: str, message: str, character: str):

        intent = classify_intent(message)
        persona_prompt = get_persona_prompt(character)

        # ================================================================
        # 1) 건강 데이터 질문 (health_query)
        # ================================================================
        if intent == "health_query":

            rag = query_health_data(message, user_id)
            similar = rag.get("similar_days", [])

            if not similar:
                system = self._build_system_prompt(persona_prompt, "health_query")
                user_prompt = f"""질문: {message}

데이터 없음. 일반 조언을 2문장으로."""
                return self._call_openai(system, user_prompt, max_tokens=200)

            top_raw = similar[0]["raw"]
            health_context = build_health_context_for_llm(top_raw)

            system = self._build_system_prompt(persona_prompt, "health_query")
            user_prompt = f"""질문: {message}

{health_context}

**2-3문장으로 핵심만 답변하세요.**"""

            return self._call_openai(system, user_prompt, max_tokens=300)

        # ================================================================
        # 2) 운동 루틴 요청 (routine_request)
        # ================================================================
        if intent == "routine_request":

            rag = query_health_data("routine", user_id)
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
        # 3) 일반 대화 (더 간결하게)
        # ================================================================
        system = self._build_system_prompt(persona_prompt, "general")
        user_prompt = f"""메시지: {message}

**1-2문장으로 짧게 응답.**"""
        return self._call_openai(system, user_prompt, max_tokens=150)
