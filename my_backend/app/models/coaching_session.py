# app/models/coaching_session.py

"""
CoachingSession 모델 (psycopg2 기반)
-----------------------------------
- 코칭 진행 상태를 저장 · 업데이트하는 모델
- ORM 없이 SQL을 직접 실행하여 구현됨
- routine_items 테이블을 기반으로 현재 진행 중인 운동/세트를 파악함

필드:
    id (UUID)
    user_id (UUID)
    routine_id (UUID)
    status: RUNNING / FINISHED
    current_exercise_index: 현재 운동 번호
    current_set: 현재 세트
"""

import uuid
from typing import Optional
from core.db import get_db_connection


class CoachingSession:

    @staticmethod
    def create_session(user_id: str, routine_id: str) -> str:
        """새 코칭 세션 생성"""
        session_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO coaching_sessions
            (id, user_id, routine_id, status, current_exercise_index, current_set)
            VALUES (%s, %s, %s, 'RUNNING', 0, 1)
        """, (session_id, user_id, routine_id))

        conn.commit()
        cur.close()
        conn.close()
        return session_id

    @staticmethod
    def get(session_id: str) -> Optional[dict]:
        """세션 조회"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, user_id, routine_id, status,
                   current_exercise_index, current_set
            FROM coaching_sessions
            WHERE id = %s
        """, (session_id,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "routine_id": row[2],
            "status": row[3],
            "current_exercise_index": row[4],
            "current_set": row[5],
        }

    @staticmethod
    def update_session(session_id: str, exercise_idx: int, set_num: int, status: str):
        """세션 진행 상태 업데이트"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE coaching_sessions
            SET current_exercise_index=%s,
                current_set=%s,
                status=%s,
                updated_at=NOW()
            WHERE id=%s
        """, (exercise_idx, set_num, status, session_id))

        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def finish_session(session_id: str):
        """세션 종료"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE coaching_sessions
            SET status='FINISHED', updated_at=NOW()
            WHERE id=%s
        """, (session_id,))

        conn.commit()
        cur.close()
        conn.close()
