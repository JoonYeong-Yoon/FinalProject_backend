from app.core.chatbot_engine.chat_generator import ChatGenerator
from app.core.chatbot_engine.fixed_responses import generate_fixed_response

# 새 캐릭터 3종만 허용
VALID_PERSONAS = {"devil_coach", "angel_coach", "booster_coach"}


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

        # 캐릭터 정규화(허용되지 않으면 기본 → booster_coach)
        persona_key = character if character in VALID_PERSONAS else "booster_coach"

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

        persona_key = character if character in VALID_PERSONAS else "booster_coach"

        response = generate_fixed_response(
            user_id=user_id,
            question_type=question_type,
            character=persona_key,
        )
        return {"character": persona_key, "response": response}
