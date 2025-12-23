"""
더미 데이터 생성 모듈
"""
import psycopg2
import os
from dotenv import load_dotenv
import uuid
import random
from datetime import datetime, timedelta

# =========================
# DB CONNECTION
# =========================
load_dotenv()

DSN = {
    "host": os.getenv("DB_HOST", "localhost"),      
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

print("DB CONNECT INFO:", DSN)  # ✅ 디버깅용 (나중에 삭제)

conn = psycopg2.connect(**DSN)


#conn = psycopg2.connect(
#    host="localhost",
#    dbname="home_training_db",
#    user="postgres",
#    password="postgres",
#    port=5432
#)
#cur = conn.cursor()

# ===============================
# ENUMS
# ===============================
GOALS = ["FAT_LOSS", "MUSCLE_GAIN", "ENDURANCE", "MAINTAIN"]
GENDERS = ["MALE", "FEMALE"]
FITNESS_LEVELS = [1, 2, 3]
TOTAL_TIMES = [20, 30, 40, 60]

STATUSES = ["FINISHED", "CANCELED", "IN_PROGRESS", "WAITING"]
CANCEL_REASONS = ["TOO_HARD", "TOO_LONG", "INJURY", "INTERRUPTED"]
INJURY_AREAS = ["SHOULDER", "ELBOW", "WAIST", "KNEE", "ANKLE"]

AI_MODEL_TYPE = "LIGHTGBM_V1"

# ===============================
# CONNECTION
# ===============================
conn = psycopg2.connect(**DSN)
cur = conn.cursor()

# ===============================
# USERS
# ===============================
def create_users(n=30):
    users = []

    for i in range(n):
        user_id = uuid.uuid4()
        gender = random.choice(GENDERS)
        fitness = random.choice(FITNESS_LEVELS)
        
        cur.execute("""
            INSERT INTO users (
                id, email, password_hash, gender, goal, fitness_level
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            str(user_id),
            f"user_{uuid.uuid4().hex[:8]}@test.com",
            "hashed_pw",
            gender,
            random.choice(GOALS),
            fitness
        ))

        # body info
        height = random.uniform(155, 185)
        weight = random.uniform(55, 90)
        bmi = round(weight / ((height / 100) ** 2), 2)
        bmr = round(
            88.36 + (13.4 * weight) + (4.8 * height) - (5.7 * random.randint(20, 45))
            if gender == "MALE"
            else 447.6 + (9.2 * weight) + (3.1 * height) - (4.3 * random.randint(20, 45)),
            2
        )

        cur.execute("""
            INSERT INTO user_body_info (
                user_id, height_cm, weight_kg, body_fat,
                skeletal_muscle, bmi, bmr
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(user_id),
            height,
            weight,
            random.uniform(18, 30),
            random.uniform(20, 35),
            bmi,
            bmr
        ))

        users.append(user_id)

    conn.commit()
    return users

# ===============================
# AI ROUTINES
# ===============================
def create_ai_routines(users):
    routines = []

    cur.execute("SELECT id FROM exercise")
    exercises = [r[0] for r in cur.fetchall()]

    for user_id in users:
        for _ in range(3):  # 추천 3개
            routine_id = uuid.uuid4()
            total_time = random.choice(TOTAL_TIMES)

            cur.execute("""
                INSERT INTO ai_recommended_routines (
                    id, user_id, goal_type, target_value,
                    recommend_strategy, total_time_min, total_calories
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                str(routine_id),
                str(user_id),
                random.choice(GOALS),
                round(random.uniform(0.7, 1.0), 2),
                AI_MODEL_TYPE,
                total_time,
                round(total_time * random.uniform(4, 7), 2)
            ))

            step = 1
            for ex in random.sample(exercises, k=random.randint(4, 6)):
                cur.execute("""
                    INSERT INTO ai_routine_items (
                        ai_routine_id, exercise_id, step_number,
                        set_count, reps, duration_sec, rest_sec
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    str(routine_id),
                    str(ex),
                    step,
                    random.randint(2, 4),
                    random.choice([8, 10, 12, 15]),
                    random.choice([30, 45, 60]),
                    random.choice([20, 30, 40])
                ))
                step += 1

            routines.append(routine_id)

    conn.commit()
    return routines

# ===============================
# ACTIVITY LOGS
# ===============================
def create_activity_logs(users, routines):
    activities = []

    for user_id in users:
        chosen = random.choice(routines)
        status = random.choice(STATUSES)

        start = datetime.now() - timedelta(minutes=random.randint(30, 120))
        end = start + timedelta(minutes=random.randint(15, 70)) if status == "FINISHED" else None

        cancel_reason = None
        injury = None

        if status == "CANCELED":
            cancel_reason = random.choice(CANCEL_REASONS)
            if cancel_reason == "INJURY":
                injury = random.choice(INJURY_AREAS)

        cur.execute("""
            INSERT INTO activity_logs (
                id, user_id, ai_routine_id, status,
                started_at, ended_at, cancellation_reason,
                injury_area, completed_ratio, total_time_min,
                total_calories, score
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            str(user_id),
            str(chosen),
            status,
            start,
            end,
            cancel_reason,
            injury,
            round(random.uniform(0.4, 1.0), 2),
            random.choice(TOTAL_TIMES),
            round(random.uniform(80, 500), 2),
            round(random.uniform(60, 95), 2) if status == "FINISHED" else None
        ))

        activities.append((user_id, chosen))

    conn.commit()
    return activities

# ===============================
# ACTIVITY DETAIL LOGS
# ===============================
def create_activity_detail_logs():
    cur.execute("""
        SELECT al.id, al.status, ari.exercise_id, ari.set_count
        FROM activity_logs al
        JOIN ai_routine_items ari ON al.ai_routine_id = ari.ai_routine_id
    """)

    rows = cur.fetchall()

    for activity_id, status, exercise_id, set_count in rows:
        if status == "WAITING":
            continue

        max_set = set_count
        if status in ("CANCELED", "IN_PROGRESS"):
            max_set = random.randint(1, set_count)

        for s in range(1, max_set + 1):
            cur.execute("""
                INSERT INTO activity_detail_logs (
                    activity_id, exercise_id,
                    set_number, reps_done, score
                )
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
            """, (
                str(activity_id),
                str(exercise_id),
                s,
                random.choice([6, 8, 10, 12, 15]),
                round(random.uniform(60, 100), 2)
            ))

    conn.commit()

# ===============================
# MAIN
# ===============================
def main():
    print("🚀 Generating dummy data v7 (ML flow)")
    users = create_users()
    routines = create_ai_routines(users)
    create_activity_logs(users, routines)
    create_activity_detail_logs()
    print("✅ Dummy data v7 created successfully")

if __name__ == "__main__":
    main()

