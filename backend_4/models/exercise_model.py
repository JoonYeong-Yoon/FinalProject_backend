# models/exercise_model.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import uuid4


# =========================
# 운동 생성
# =========================
def create_exercise(db: Session, data: dict):
    exercise_id = str(uuid4())

    query = text("""
        INSERT INTO exercise (
            id,
            name,
            type,
            posture,
            category_1,
            category_2,
            difficulty,
            met,
            description,
            thumbnail_url,
            video_url
        )
        VALUES (
            :id,
            :name,
            :type,
            :posture,
            :category_1,
            :category_2,
            :difficulty,
            :met,
            :description,
            :thumbnail_url,
            :video_url
        )
    """)

    db.execute(query, {
        "id": exercise_id,
        "name": data.get("name"),
        "type": data.get("type"),
        "posture": data.get("posture"),
        "category_1": data.get("category_1"),
        "category_2": data.get("category_2"),
        "difficulty": data.get("difficulty"),
        "met": data.get("met"),
        "description": data.get("description"),
        "thumbnail_url": data.get("thumbnail_url"),
        "video_url": data.get("video_url"),
    })

    db.commit()
    return exercise_id


# =========================
# 운동 영상 URL 업데이트
# =========================
def update_exercise_video(db: Session, exercise_id: str, video_url: str):
    query = text("""
        UPDATE exercise
        SET video_url = :video_url
        WHERE id = :exercise_id
    """)

    db.execute(query, {
        "exercise_id": exercise_id,
        "video_url": video_url
    })

    db.commit()


# =========================
# 운동 존재 여부 확인
# =========================
def get_exercise_by_id(db: Session, exercise_id: str):
    query = text("""
        SELECT * FROM exercise
        WHERE id = :exercise_id
    """)

    return db.execute(query, {
        "exercise_id": exercise_id
    }).mappings().first()
