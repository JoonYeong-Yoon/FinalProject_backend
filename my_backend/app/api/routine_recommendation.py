# app/api/routine_recommendation.py
"""
루틴 추천 라우터
- POST /api/v1/routines/recommend
- 입력: user_id (필수), total_time_min (선택, 한국어 UI)
- 내부는 영어 기반으로 동작. DB에서 로드 후 user_info는 영어 필드 사용.
- 응답은 한국어 표시용 필드(name_ko, category_ko 등)를 추가해 반환.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import datetime
from decimal import Decimal

from core.db import get_db_connection  # 프로젝트의 DB helper
from services.routine_generator.builder import generate_three_strategy_routines
from services.routine_generator.mappings import (
    GOAL_EN_TO_KO, GOAL_KO_TO_EN,
    EXERCISE_EN_TO_KO, EXERCISE_KO_TO_EN,
    map_en_to_ko, map_ko_to_en, CATEGORY1_EN_TO_KO
)

router = APIRouter(prefix="/api/v1/routines", tags=["routines"])

class RecommendReq(BaseModel):
    user_id: str
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
    strategy: str
    total_time_min: float
    total_calories: float
    score: float
    exercises: List[ExerciseOut]

@router.post("/recommend", response_model=List[RoutineOut])
def recommend_routine(req: RecommendReq):
    # 1) 시간 클램프
    time_min = max(10, min(60, int(req.total_time_min or 45)))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # users + user_body_info 조회 (DB 필드는 영어)
        cur.execute("""
            SELECT u.id, u.goal, u.fitness_level, u.gender, u.birthdate,
                   b.height_cm, b.weight_kg, b.body_fat, b.skeletal_muscle, b.bmr, b.visceral_fat_level, b.water
            FROM users u
            JOIN user_body_info b ON u.id = b.user_id
            WHERE u.id = %s
        """, (req.user_id,))
        rec = cur.fetchone()
        if not rec:
            raise HTTPException(status_code=404, detail="User not found")

        # unpack (DB 순서와 일치)
        uid, goal_en, fitness_level, gender, birthdate, height_cm, weight_kg, body_fat, skeletal_muscle, bmr, visceral, water = rec

        # 안전한 타입 변환: Decimal -> float
        def _to_float(v):
            if v is None:
                return None
            if isinstance(v, Decimal):
                return float(v)
            try:
                return float(v)
            except:
                return None

        # 나이, bmi 계산
        today = datetime.date.today()
        age = 0
        if birthdate:
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        bmi = 0.0
        fh = _to_float(height_cm)
        fw = _to_float(weight_kg)
        if fh and fh > 0:
            bmi = round(fw / ((fh/100.0)**2), 2)

        user_info = {
            "user_id": str(uid),
            "goal": goal_en,  # 영어 (DB 표준)
            "fitness_level": int(fitness_level) if fitness_level is not None else 1,
            "gender": gender,
            "age": int(age),
            "bmi": bmi,
            "body_fat": _to_float(body_fat),
            "skeletal_muscle": _to_float(skeletal_muscle),
            "weight_kg": _to_float(weight_kg),
            "bmr": _to_float(bmr),
            "visceral_fat_level": _to_float(visceral),
            "water": _to_float(water),
        }

        # exercise 카탈로그 로드 (DB에는 영어로 저장했다고 가정)
        cur.execute("SELECT id, name, type, posture, category_1, category_2, difficulty, MET, description, caution FROM exercise;")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        catalog = [dict(zip(cols, r)) for r in rows]

    finally:
        if conn:
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


@router.post("/selected-recommend", response_model=RoutineOut)
def save_recommend_routine(req: RecommendReq):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # users + user_body_info 조회 (DB 필드는 영어)
        cur.execute("""
            INSERT INTO 
            SELECT u.id, u.goal, u.fitness_level, u.gender, u.birthdate,
                   b.height_cm, b.weight_kg, b.body_fat, b.skeletal_muscle, b.bmr, b.visceral_fat_level, b.water
            FROM users u
            JOIN user_body_info b ON u.id = b.user_id
            WHERE u.id = %s
        """, (req.user_id,))
        rec = cur.fetchone()

    finally:
        if conn:
            conn.close()
