# app/services/tts_service.py
"""
Edge TTS 서비스
- generate_tts_audio(text) -> base64 mp3 문자열 반환

pip install edge_tts
"""
import edge_tts
import base64
import asyncio
from typing import Dict

VOICE = "ko-KR-SunHiNeural"
RATE = "+0%"
VOLUME = "+0%"

# -------------------------
# In-memory TTS cache
# -------------------------
_TTS_CACHE: Dict[str, str] = {}

# -------------------------
# Core async generator
# -------------------------
async def _generate_audio_async(text: str) -> bytes:
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        volume=VOLUME,
    )

    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]

    return audio_bytes


# -------------------------
# Public API
# -------------------------
async def generate_tts_audio(text: str) -> str:
    """
    Generate base64 mp3 string from text.
    Safe for repeated / concurrent calls.
    """

    if not text or not text.strip():
        return ""

    # 1️⃣ Cache hit
    if text in _TTS_CACHE:
        return _TTS_CACHE[text]

    # 2️⃣ Retry (max 2)
    for _ in range(2):
        try:
            audio_bytes = await _generate_audio_async(text)

            if not audio_bytes:
                continue

            # base64 encode
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # sanitize (Swagger / JSON safe)
            audio_b64 = (
                audio_b64
                .replace("\n", "")
                .replace("\r", "")
                .replace(" ", "")
            )

            # save cache
            _TTS_CACHE[text] = audio_b64
            return audio_b64

        except Exception as e:
            print("❌ Edge TTS error (retrying):", e)
            await asyncio.sleep(0.3)

    # 3️⃣ Fail-safe
    print("❌ Edge TTS failed completely:", text)
    return ""




