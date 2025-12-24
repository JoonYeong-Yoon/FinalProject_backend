from app.core.chatbot_engine.chat_generator import ChatGenerator
from app.core.chatbot_engine.fixed_responses import generate_fixed_response

# 8가지 캐릭터 허용 (5가지 신규 + 3가지 레거시)
VALID_PERSONAS = {
    # 새로운 5가지 전문 캐릭터
    "default",      # 헬스 코치 지니
    "trainer",      # 근육맨 트레이너
    "yoga",         # 요가 마스터 수련
    "cardio",       # 카디오 퀸
    "diet",         # 영양사 민희
    # 레거시 캐릭터 (하위 호환성)
    "devil_coach",
    "angel_coach",
    "booster_coach",
}


class ChatService:
    """
    Chat 관련 비즈니스 로직을 담당하는 Service 계층.
    ChatGenerator가 실제 LLM 메시지 생성 역할을 수행한다.
    """

    def __init__(self):
        self.generator = ChatGenerator()

    # -------------------------------------------
    # 1) 자유형 (intent → sentiment → RAG → LLM)
    # -------------------------------------------
    def handle_chat(self, user_id: str, message: str, character: str):

        # 캐릭터 정규화(허용되지 않으면 기본 → default)
        persona_key = character if character in VALID_PERSONAS else "default"

        # ChatGenerator 내부에서 persona_prompt + LLM 호출 수행
        response = self.generator.generate(
            user_id=user_id,
            message=message,
            character=persona_key,
        )

        return {"character": persona_key, "response": response}

    # -------------------------------------------
    # 2) 고정형
    # -------------------------------------------
    @staticmethod
    def handle_fixed_chat(user_id: str, question_type: str, character: str):

        persona_key = character if character in VALID_PERSONAS else "default"

        response = generate_fixed_response(
            user_id=user_id,
            question_type=question_type,
            character=persona_key,
        )
        return {"character": persona_key, "response": response}
