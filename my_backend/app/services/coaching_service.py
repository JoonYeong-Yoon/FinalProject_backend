# app/services/coaching_service.py
"""
코칭 서비스 (루틴 진행 관리)
-----------------------------------
- start_coaching: 코칭 시작
- next_step: 다음 세트 혹은 다음 운동 이동
- finish_coaching: 세션 종료
- routine_items 로드 및 exercise 정보 로드 포함
"""

from typing import List, Dict
from core.db import get_db_connection
from models.coaching_session import CoachingSession
from services.coaching_text import (
    generate_start_text,
    generate_next_text,
    generate_finish_text,
)


def load_routine_items(routine_id: str) -> List[Dict]:
    """routine_items + exercise 테이블 JOIN하여 하나의 운동 리스트 생성"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            ri.exercise_id,
            e.name,
            ri.set_count,
            ri.reps,
            ri.duration_sec,
            ri.rest_sec,
            e.description,
            e.caution
        FROM ai_routine_items ri      
        JOIN exercise e ON ri.exercise_id = e.id
        WHERE ri.ai_routine_id = %s  
        ORDER BY ri.step_number
    """, (routine_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "exercise_id": r[0],
            "name": r[1],
            "set_count": r[2],
            "reps": r[3],
            "duration_sec": r[4],
            "rest_sec": r[5],
            "description": r[6],
            "caution": r[7],
        })

    return result


def start_coaching(user_id: str, routine_id: str) -> dict:
    session_id = CoachingSession.create_session(user_id, routine_id)

    exercises = load_routine_items(routine_id)
    first_ex = exercises[0]

    coaching_text = generate_start_text(first_ex)

    return {
        "session_id": session_id,
        "exercise": first_ex,
        "set": 1,
        "coaching_text": coaching_text
    }



def next_step(session_id: str) -> dict:
    """다음 세트 or 다음 운동으로 이동"""
    sess = CoachingSession.get(session_id)
    if not sess or sess["status"] != "RUNNING":
        return {"error": "Invalid session"}

    exercises = load_routine_items(sess["routine_id"])
    idx = sess["current_exercise_index"]
    set_num = sess["current_set"]

    ex = exercises[idx]

    # 같은 운동 내 다음 세트
    if set_num < ex["set_count"]:
        new_set = set_num + 1
        CoachingSession.update_session(session_id, idx, new_set, "RUNNING")

        coaching = generate_next_text(ex["name"], new_set)

        return {
            "exercise": ex,
            "set": new_set,
            "coaching_text": coaching
        }

    # 다음 운동
    if idx + 1 < len(exercises):
        next_idx = idx + 1
        CoachingSession.update_session(session_id, next_idx, 1, "RUNNING")

        next_ex = exercises[next_idx]
        coaching = generate_next_text(next_ex["name"], 1)

        return {
            "exercise": next_ex,
            "set": 1,
            "coaching_text": coaching
        }

    # 루틴 종료
    CoachingSession.finish_session(session_id)

    coaching = generate_finish_text(
        completion_ratio=sess["completed_ratio"]
    )

    return {
        "coaching_text": coaching
    }

def finish_coaching(session_id: str):
    """강제로 종료"""
    CoachingSession.finish_session(session_id)
    return {"message": "코칭 세션 종료"}