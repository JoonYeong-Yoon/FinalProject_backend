
"""
Edge TTS 서비스
- generate_tts_audio(text) -> base64 mp3 문자열 반환

pip install edge_tts
"""
# app/services/tts_service.py

import edge_tts
import base64

VOICE = "ko-KR-SunHiNeural"  # 한국어 여성 (운동 코칭에 적합)
# VOICE = "ko-KR-InJoonNeural"  # 남성 음성 원하면 이걸로 교체

async def generate_tts_audio(text: str) -> str:
    if not text or not text.strip():
        return ""

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=VOICE,
            rate="+0%",     # 말 속도
            volume="+0%"    # 음량
        )

        audio_bytes = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if not audio_bytes:
            return ""

        return base64.b64encode(audio_bytes).decode("utf-8")

    except Exception as e:
        print("❌ Edge TTS error:", e)
        return ""



