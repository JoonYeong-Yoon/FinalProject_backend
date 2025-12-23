# services/tts_helper.py
"""
async TTS를 sync 서비스에서 안전하게 사용하기 위한 헬퍼
- FastAPI sync 방식 + psycopg2 기반 서비스에서 Edge TTS async 함수 호출
"""

import asyncio
from services.tts_service import generate_tts_audio

def build_tts_payload(text: str) -> dict:
    if not text or not text.strip():
        return {"tts_text": "", "tts_audio": ""}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 이미 루프가 있으면 태스크로 실행
        audio = loop.create_task(generate_tts_audio(text))
        audio = loop.run_until_complete(audio)  # uvicorn 환경에선 OK
    else:
        audio = asyncio.run(generate_tts_audio(text))

    # 표시/파싱 문제 방지
    audio = (audio or "").replace("\n", "").replace("\r", "").replace(" ", "")

    return {"tts_text": text, "tts_audio": audio}


