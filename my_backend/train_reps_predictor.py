"""
RepsPredictor 모델 학습 스크립트

[개요]
- PostgreSQL DB에서 실제 운동 로그 데이터를 불러와
  운동별 권장 반복 횟수(target_reps)를 예측하는 LightGBM 모델을 학습.
- 학습이 끝나면 아래 두 파일을 생성.

[출력 파일]
1) app/ai_models/reps_predictor_model.pkl
2) app/ai_models/label_encoders.pkl

[중요]
- Predictor 코드와 feature 수 / 순서가 100% 일치하도록 설계됨
"""

import os
import pickle
import psycopg2
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from lightgbm import LGBMRegressor

# ===============================
# 1. DB 설정
# ===============================

DSN = {
    "dbname": "home_training_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

MODEL_PATH = "app/ai_models/reps_predictor_model.pkl"
ENCODER_PATH = "app/ai_models/label_encoders.pkl"


# ===============================
# 2. 학습 데이터 로딩
# ===============================

def get_training_data() -> pd.DataFrame:
    """
    실제 운동 로그 기반 학습 데이터 로딩
    """
    query = """
    SELECT
        (adl.reps_done / adl.set_number)            AS target_reps,
        u.gender                                   AS gender,
        u.goal                                     AS goal,
        u.fitness_level                            AS fitness_level,
        latest_ubi.bmi                             AS bmi,
        latest_ubi.body_fat                        AS body_fat,
        latest_ubi.skeletal_muscle                 AS skeletal_muscle,
        adl.exercise_id                            AS exercise_id,
        e.category_1                               AS exercise_category,
        latest_ubi.weight_kg                       AS user_current_weight,
        prev_adl.reps_done                         AS previous_set_reps,
        prev_adl.score                             AS previous_set_score
    FROM activity_detail_logs adl
    JOIN activity_logs al ON adl.activity_id = al.id
    JOIN users u ON al.user_id = u.id
    JOIN exercise e ON adl.exercise_id = e.id
    LEFT JOIN (
        SELECT DISTINCT ON (user_id)
            user_id,
            bmi,
            body_fat,
            skeletal_muscle,
            weight_kg
        FROM user_body_info
        ORDER BY user_id, updated_at DESC
    ) latest_ubi ON al.user_id = latest_ubi.user_id
    LEFT JOIN activity_detail_logs prev_adl
        ON adl.activity_id = prev_adl.activity_id
       AND adl.exercise_id = prev_adl.exercise_id
       AND prev_adl.set_number = adl.set_number - 1
    WHERE
        al.status = 'FINISHED'
        AND adl.score >= 70
        AND adl.reps_done IS NOT NULL
        AND adl.set_number > 1
    """

    conn = psycopg2.connect(**DSN)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    return df


# ===============================
# 3. 모델 학습
# ===============================

def train_model():
    print("🔄 Loading training data...")
    df = get_training_data()

    if df.empty:
        raise RuntimeError("❌ 학습할 데이터가 없습니다.")

    print(f"✅ Raw rows: {len(df)}")

    # 결측치 제거
    df.dropna(subset=["previous_set_reps", "previous_set_score"], inplace=True)
    print(f"✅ After dropna: {len(df)}")

    # ===============================
    # 3-1. 범주형 인코딩
    # ===============================

    categorical_cols = [
        "gender",
        "goal",
        "exercise_id",
        "exercise_category",
    ]

    encoders = {}

    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # ===============================
    # 3-2. 입력 / 출력 분리
    # ===============================

    FEATURE_COLUMNS = [
        "gender",
        "goal",
        "fitness_level",
        "bmi",
        "body_fat",
        "skeletal_muscle",
        "exercise_id",
        "exercise_category",
        "user_current_weight",
        "previous_set_reps",
        "previous_set_score",
    ]

    X = df[FEATURE_COLUMNS]
    y = df["target_reps"]

    print(f"🧠 Feature count: {X.shape[1]} (must be 11)")

    # ===============================
    # 3-3. Train / Test 분리
    # ===============================

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ===============================
    # 3-4. LightGBM 학습
    # ===============================

    model = LGBMRegressor(
        n_estimators=400,
        learning_rate=0.03,
        max_depth=6,
        num_leaves=48,
        min_child_samples=15,
        random_state=42,
    )

    print("🤖 Training model...")
    model.fit(X_train, y_train)

    print("✅ Training completed")
    print(f"📌 Model n_features_: {model.n_features_}")

    # ===============================
    # 4. 모델 & 인코더 저장
    # ===============================

    os.makedirs("app/ai_models", exist_ok=True)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(encoders, f)

    print("💾 Model saved:", MODEL_PATH)
    print("💾 Encoders saved:", ENCODER_PATH)


# ===============================
# 5. 실행 진입점
# ===============================

if __name__ == "__main__":
    train_model()
    print("🎉 RepsPredictor training pipeline finished successfully.")
