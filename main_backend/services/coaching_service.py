# app/services/coaching_service.py
"""
코칭 서비스 (루틴 진행 관리)
"""

import uuid
import asyncio
from typing import Dict, Optional
from jose import jwt

from core.db import get_db_connection
from services.coaching_text import (
    generate_start_text,
    generate_next_text,
    generate_rest_text,
    generate_finish_text,
    generate_exercise_intro_text
)
from services.tts_service import generate_tts_audio
from config.settings import settings


# ---------------------------
# TTS helper (동기 래퍼)
# ---------------------------
def build_tts_payload(text: str) -> Dict[str, str]:
    if not text or not text.strip():
        return {"tts_text": "", "tts_audio": ""}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            audio = loop.run_until_complete(generate_tts_audio(text))
        else:
            audio = asyncio.run(generate_tts_audio(text))
    except RuntimeError:
        audio = asyncio.run(generate_tts_audio(text))

    audio = (audio or "").replace("\n", "").replace("\r", "").replace(" ", "")
    return {"tts_text": text, "tts_audio": audio}


# ===========================
# START COACHING
# ===========================
def start_coaching_session(
        # user_id: str, 
        ai_routine_id,
        token
        ):

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")

        conn = get_db_connection()
        cur = conn.cursor()

        # 루틴 아이템 확인
        cur.execute(
            """
            SELECT exercise_id, set_count, reps, rest_sec, duration_sec
            FROM ai_routine_items
            WHERE ai_routine_id = %s
            ORDER BY step_number
            LIMIT 1
            """,
            (ai_routine_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("ai_routine_items not found")

        exercise_id, set_count, reps, rest_sec, duration_sec = row

        # 세션 생성
        session_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO coaching_sessions (
                id, user_id, ai_routine_id,
                status, current_exercise_index, current_set
            )
            VALUES (%s, %s, %s, 'RUNNING', 0, 1)
            """,
            (session_id, user_id, ai_routine_id),
        )

        conn.commit()

        exercise_dict = {
            "exercise_id": exercise_id,
            "sets": set_count,
            "reps": reps,
            "rest_sec": rest_sec,
            "duration_sec": duration_sec,
        }

        text = generate_start_text(exercise_dict)
        tts = build_tts_payload(text)

        return {
            "coaching_session_id": session_id,
            "current_step": 1,
            "exercise": exercise_dict,
            **tts,
        }

    finally:
        conn.close()


# ===========================
# NEXT STEP
# ===========================
def next_step(coaching_session_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1️⃣ 세션 조회
        cur.execute("""
            SELECT user_id,
                   ai_routine_id,
                   current_exercise_index,
                   current_set,
                   status
            FROM coaching_sessions
            WHERE id = %s
        """, (coaching_session_id,))
        row = cur.fetchone()

        if not row:
            raise ValueError("Coaching session not found")

        user_id, ai_routine_id, current_exercise_index, current_set, status = row

        if status != "RUNNING":
            return {"status": status}

        # 2️⃣ 현재 운동 조회 (step_number는 1-based)
        step_number = current_exercise_index + 1

        cur.execute("""
            SELECT
                i.exercise_id,
                i.set_count,
                i.reps,
                i.rest_sec,
                i.duration_sec,
                e.description,
                e.caution
            FROM ai_routine_items i
            JOIN exercise e ON i.exercise_id = e.id
            WHERE i.ai_routine_id = %s
            AND i.step_number = %s
        """, (ai_routine_id, step_number))

        exercise = cur.fetchone()

        # 3️⃣ 더 이상 운동이 없으면 FINISHED
        if not exercise:
            cur.execute("""
                UPDATE coaching_sessions
                SET status = 'FINISHED',
                    updated_at = NOW()
                WHERE id = %s
            """, (coaching_session_id,))

            text = generate_finish_text(1.0)
            tts = build_tts_payload(text)

            conn.commit()
            return {
                "status": "FINISHED",
                **tts
            }

        exercise_id, set_count, reps, rest_sec, duration_sec, description, caution = exercise

        exercise_dict = {
            "exercise_id": exercise_id,
            "sets": set_count,
            "reps": reps,
            "rest_sec": rest_sec,
            "duration_sec": duration_sec,
            "description": description,
            "caution": caution,
        }

        # =========================
        # 🔀 분기 로직
        # =========================

        # 4️⃣ 같은 운동 - 다음 세트
        if current_set < set_count:
            next_set = current_set + 1

            cur.execute("""
                UPDATE coaching_sessions
                SET current_set = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (next_set, coaching_session_id))

            text = generate_next_text(exercise_dict, next_set)
            tts = build_tts_payload(text)

            conn.commit()
            return {
                "coaching_session_id": coaching_session_id,
                "exercise": exercise_dict,
                **tts
            }

        # 5️⃣ 마지막 세트 종료 → 휴식
        elif current_set == set_count:
            cur.execute("""
                UPDATE coaching_sessions
                SET current_set = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (current_set + 1, coaching_session_id))

            text = generate_rest_text(rest_sec)
            tts = build_tts_payload(text)

            conn.commit()
            return {
                "coaching_session_id": coaching_session_id,
                "exercise": exercise_dict,
                **tts
            }

        # 6️⃣ 다음 운동으로 이동
        else:
            cur.execute("""
                UPDATE coaching_sessions
                SET current_exercise_index = %s,
                    current_set = 1,
                    updated_at = NOW()
                WHERE id = %s
            """, (current_exercise_index + 1, coaching_session_id))

            intro_text = generate_exercise_intro_text(exercise_dict)
            set_text = generate_next_text(exercise_dict, 1)

            # 설명 + 주의 + 세트 시작을 한 번에
            full_text = f"{intro_text} {set_text}".strip()

            tts = build_tts_payload(full_text)

            conn.commit()
            return {
                "coaching_session_id": coaching_session_id,
                "exercise": exercise_dict,
                **tts
            }

    finally:
        conn.close()



# ===========================
# CANCEL COACHING
# ===========================
def cancel_coaching_session(
    coaching_session_id: str,
    cancellation_reason: str,
    injury_area: Optional[str],
):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT user_id, ai_routine_id,
                   current_exercise_index, current_set, status
            FROM coaching_sessions
            WHERE id = %s
            """,
            (coaching_session_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Coaching session not found")

        user_id, ai_routine_id, idx, cur_set, status = row
        if status != "RUNNING":
            raise ValueError("Session is not running")

        cur.execute(
            """
            UPDATE coaching_sessions
            SET status = 'CANCELLED', updated_at = NOW()
            WHERE id = %s
            """,
            (coaching_session_id,),
        )

        # 전체 세트 수
        cur.execute(
            """
            SELECT COALESCE(SUM(set_count), 0)
            FROM ai_routine_items
            WHERE ai_routine_id = %s
            """,
            (ai_routine_id,),
        )
        total_sets = cur.fetchone()[0]

        # 완료된 세트 수
        cur.execute(
            """
            SELECT COALESCE(SUM(set_count), 0)
            FROM ai_routine_items
            WHERE ai_routine_id = %s
              AND step_number < %s
            """,
            (ai_routine_id, idx + 1),
        )
        completed_before = cur.fetchone()[0]

        completed_sets = completed_before + max(cur_set - 1, 0)
        completed_ratio = round(
            completed_sets / total_sets if total_sets > 0 else 0.0, 2
        )

        cur.execute(
            """
            INSERT INTO activity_logs (
                user_id, ai_routine_id, coaching_session_id,
                status, cancellation_reason, injury_area,
                completed_ratio, ended_at
            )
            VALUES (%s, %s, %s, 'CANCELLED', %s, %s, %s, NOW())
            """,
            (
                user_id,
                ai_routine_id,
                coaching_session_id,
                cancellation_reason,
                injury_area,
                completed_ratio,
            ),
        )

        conn.commit()
        return {"status": "CANCELLED"}

    finally:
        conn.close()

def finish_coaching_session(coaching_session_id: str):
    """
    정상적으로 운동을 끝냈을 때 호출되는 종료 처리
    - coaching_sessions → FINISHED
    - activity_logs → FINISHED + completed_ratio = 1.0
    """

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1️⃣ 세션 조회
        cur.execute("""
            SELECT user_id,
                   ai_routine_id,
                   status
            FROM coaching_sessions
            WHERE id = %s
        """, (coaching_session_id,))
        row = cur.fetchone()

        if not row:
            raise ValueError("Coaching session not found")

        user_id, ai_routine_id, status = row

        if status != "RUNNING":
            raise ValueError("Session is not running")

        # 2️⃣ coaching_sessions 종료 처리
        cur.execute("""
            UPDATE coaching_sessions
            SET status = 'FINISHED',
                updated_at = NOW()
            WHERE id = %s
        """, (coaching_session_id,))

        # 3️⃣ activity_logs INSERT (정상 종료)
        cur.execute("""
            INSERT INTO activity_logs (
                user_id,
                ai_routine_id,
                coaching_session_id,
                status,
                completed_ratio,
                ended_at
            )
            VALUES (%s, %s, %s, 'FINISHED', %s, NOW())
        """, (
            user_id,
            ai_routine_id,
            coaching_session_id,
            1.0
        ))

        conn.commit()
        return {"status": "FINISHED"}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
