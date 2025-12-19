# app/api/routine_recommendation.py
"""
루틴 추천 라우터
- POST /api/v1/routines/recommend
- 입력: user_id (필수), total_time_min (선택, 한국어 UI)
- 내부는 영어 기반으로 동작. DB에서 로드 후 user_info는 영어 필드 사용.
- 응답은 한국어 표시용 필드(name_ko, category_ko 등)를 추가해 반환.
"""
import traceback

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List
import datetime
from decimal import Decimal
from jose import jwt, JWTError

from core.db import get_db_connection  # 프로젝트의 DB helper
from services.routine_generator.builder import generate_three_strategy_routines
from services.routine_generator.mappings import (
    GOAL_EN_TO_KO, GOAL_KO_TO_EN,
    EXERCISE_EN_TO_KO, EXERCISE_KO_TO_EN,
    map_en_to_ko, map_ko_to_en, CATEGORY1_EN_TO_KO
)
from config.settings import settings

router = APIRouter(prefix="/api/v1/routines", tags=["routines"])

class RecommendReq(BaseModel):
    # user_id: str
    total_time_min: Optional[int] = 45

class ExerciseOut(BaseModel):
    exercise_id: str
    name: str
    sets: int
    reps: int
    rest_sec: int
    duration_sec: int
    est_calories: float
    # Korean friendly fields 추가 (응답에 포함)
    name_ko: Optional[str] = None
    category_ko: Optional[str] = None

class RoutineOut(BaseModel):
    ai_routine_id: str
    strategy: str
    total_time_min: float
    total_calories: float
    score: Optional[float] = None
    exercises: List[ExerciseOut]

    class Config:
        orm_mode = True
        extra = "forbid"
class SelectRoutineReq(BaseModel):
    user_id: str

       
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/users/login")


@router.post("/recommend", response_model=List[RoutineOut])
def recommend_routine(req: RecommendReq, token: str = Depends(oauth2_scheme)):
    try:
        # 1) 시간 클램프
        time_min = max(10, min(60, int(req.total_time_min or 45)))
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        
        conn = get_db_connection()
        cur = conn.cursor()
        # users + user_body_info 조회 (DB 필드는 영어)
        cur.execute("""
            SELECT u.id, u.goal, u.fitness_level, u.gender, u.birthdate,
                   b.height_cm, b.weight_kg, b.body_fat, b.skeletal_muscle, b.bmr, b.visceral_fat_level, b.water
            FROM users u
            JOIN user_body_info b ON u.id = b.user_id
            WHERE u.id = %s
        """, (user_id,))
        rec = cur.fetchone()
        if not rec:
            raise HTTPException(status_code=404, detail="User not found")

        # unpack (DB 순서와 일치)

        (
            uid, goal_en, fitness_level, gender, birthdate,
            height_cm, weight_kg, body_fat, skeletal_muscle,
            bmr, visceral, water
        ) = rec

        def _to_float(v):
            if v is None:
                return None
            if isinstance(v, Decimal):
                return float(v)
            return float(v)

        # 3️⃣ 파생 데이터 계산
        today = datetime.date.today()
        age = 0
        if birthdate:
            age = today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )

        bmi = 0.0
        if height_cm and weight_kg:
            bmi = round(
                _to_float(weight_kg) / ((_to_float(height_cm) / 100) ** 2),
                2
            )
        weight = _to_float(weight_kg) or 70.0
        height = _to_float(height_cm) or 170.0
        user_info = {
            "user_id": str(uid),
            "goal": (goal_en or "MAINTAIN").upper(),
            "fitness_level": int(fitness_level or 1),
            "gender": gender or "M",
            "age": age or 30,
            "bmi": round(weight / ((height / 100) ** 2), 2),
            "weight_kg": weight,
            "bmr": _to_float(bmr) or 1500.0,
        }

        # 4️⃣ 운동 카탈로그 로드
        # caution
        cur.execute("""
            SELECT id, name, type, posture, category_1,
                   category_2, difficulty, MET, description
            FROM exercise
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        catalog = [dict(zip(cols, r)) for r in rows]

        # 5️⃣ AI 루틴 생성
        routines = generate_three_strategy_routines(
            user_info, catalog, time_min
        )

        # 6️⃣ 트랜잭션 시작 (원자성 보장)
        for r in routines:
            ai_routine_id = save_ai_routine(conn, user_info, r)
            r["ai_routine_id"] = ai_routine_id

        conn.commit()

        # 7️⃣ 응답 변환
        out: List[RoutineOut] = []

        for r in routines:
            ex_list = []
            for it in r["exercises"]:
                name_en = it.get("name")
                name_ko = map_en_to_ko(name_en, EXERCISE_EN_TO_KO)
                cat_en = (it.get("exercise_meta", {}).get("category_1") or "").upper()
                cat_ko = map_en_to_ko(cat_en, CATEGORY1_EN_TO_KO)

                ex_list.append({
                    "exercise_id": it.get("exercise_id"),
                    "name": name_ko,
                    "sets": it.get("sets", 1),
                    "reps": it.get("reps", 0),
                    "rest_sec": it.get("rest_sec", 60),
                    "duration_sec": it.get("duration_sec", 0),
                    "est_calories": float(it.get("est_calories") or 0.0),
                    "name_ko": name_ko,
                    "category_ko": cat_ko,
                })

            out.append({
                "ai_routine_id": r["ai_routine_id"],
                "strategy": r["strategy"],
                "total_time_min": r["total_time_min"],
                "total_calories": r["total_calories"],
                "score": float(r.get("score") or 0.0),
                "exercises": ex_list,
            })

        return out
    

    except Exception as e:
        print("🔥 RECOMMEND ERROR 🔥")
        traceback.print_exc()
        raise

    finally:
        conn.close()

    # 2) generate routines (모든 내부는 영어 기반)
    routines = generate_three_strategy_routines(user_info, catalog, time_min)

    # 3) 응답 변환 — 영어 → 한국어 필드 추가 (원본 영어 값은 유지)
    out = []
    for r in routines:
        ex_list = []
        for it in r["exercises"]:
            name_en = it.get("name")
            # 영어->한국어 (없으면 영어 그대로)
            name_ko = map_en_to_ko(name_en, EXERCISE_EN_TO_KO)
            cat_en = (it.get("exercise_meta", {}).get("category_1") or "").upper()
            cat_ko = map_en_to_ko(cat_en, CATEGORY1_EN_TO_KO)
            ex_list.append({
                "exercise_id": it.get("exercise_id"),
                "name": name_ko,  # 프론트에서는 name에 한국어 표기(요청에 맞춤)
                "sets": it.get("sets"),
                "reps": it.get("reps"),
                "rest_sec": it.get("rest_sec"),
                "duration_sec": it.get("duration_sec"),
                "est_calories": it.get("est_calories"),
                # 상세 응답에 영어도 필요하면 추가 필드로 넣을 수 있음
                "name_en": name_en,
                "category_en": cat_en,
                "name_ko": name_ko,
                "category_ko": cat_ko,
            })

        out.append({
            "strategy": r.get("strategy"),
            "total_time_min": r.get("total_time_min"),
            "total_calories": r.get("total_calories"),
            "score": r.get("score"),
            "exercises": ex_list
        })
    return out


# =========================
# Save AI Routine (Service)
# =========================

def save_ai_routine(conn, user_info: dict, routine: dict) -> str:
    cur = conn.cursor()
    # recommend_strategy,

    cur.execute("""
        INSERT INTO ai_recommended_routines (
            user_id,
            goal_type,
            target_value,
            total_time_min,
            total_calories
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_info["user_id"],
        user_info["goal"],
        routine.get("total_time_min"),
        # routine["strategy"],
        routine["total_time_min"],
        routine["total_calories"],
    ))

    ai_routine_id = cur.fetchone()[0]

    for idx, ex in enumerate(routine["exercises"], start=1):
        cur.execute("""
            INSERT INTO ai_routine_items (
                ai_routine_id,
                exercise_id,
                step_number,
                set_count,
                reps,
                duration_sec,
                rest_sec
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            ai_routine_id,
            ex["exercise_id"],
            idx,
            ex["sets"],
            ex["reps"],
            ex["duration_sec"],
            ex["rest_sec"],
        ))

    return str(ai_routine_id)

# =========================
# Select AI Routine
# =========================

@router.post("/{ai_routine_id}/select")
def select_ai_routine(ai_routine_id: str, token: str = Depends(oauth2_scheme)):

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        

        # 1️⃣ AI 루틴 확인
        # , recommend_strategy
        cur.execute("""
            SELECT user_id, goal_type,
                   total_time_min, total_calories
            FROM ai_recommended_routines
            WHERE id = %s
        """, (ai_routine_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="AI routine not found")

        (
            ai_user_id,
            goal_type,
            # recommend_strategy,
            total_time_min,
            total_calories,
        ) = row

        if str(ai_user_id) != user_id:
            raise HTTPException(status_code=403, detail="Not your routine")

        # 2️⃣ user_routines 생성
        # recommend_strategy,goal_type,source_ai_routine_id,

        cur.execute("""
            INSERT INTO activity_logs (
                user_id,
                total_time_min,
                total_calories,
                status
            )
            VALUES (%s, %s, %s, 'CONFIRMED')
            RETURNING id
        """, (
            user_id,
            # goal_type,
            # ai_routine_id,
            # recommend_strategy,
            total_time_min,
            total_calories,
        ))

        user_routine_id = cur.fetchone()[0]

        # # 3️⃣ 아이템 복사
        # # step_number drop
        # cur.execute("""
        #     SELECT exercise_id, set_count,
        #            reps, duration_sec, rest_sec
        #     FROM ai_routine_items
        #     WHERE ai_routine_id = %s
        #     ORDER BY step_number
        # """, (ai_routine_id,))

        # for ex in cur.fetchall():
        #     # user_routine_items -> routine_items
        #     # user_routine_id -> routine_id
        #     # step_number
        #     cur.execute("""
        #         INSERT INTO routine_items (
        #             routine_id,
        #             exercise_id,
        #             set_count,
        #             reps,
        #             duration_sec,
        #             rest_sec
        #         )
        #         VALUES (%s, %s, %s, %s, %s, %s)
        #     """, (user_routine_id, *ex))

        # conn.commit()

        return {
            "user_routine_id": str(user_routine_id),
            "status": "CONFIRMED",
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


