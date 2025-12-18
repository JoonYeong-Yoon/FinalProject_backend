"""
RoutineScorer 모델 학습 스크립트 (전체 실행용)

[개요]
- 사용자의 실제 운동 완료 로그를 기반으로
  "해당 루틴이 사용자에게 얼마나 적절했는지"를 점수(0~100)로 예측하는 모델을 학습한다.
- 이 점수는 이후 루틴 추천 시 랭킹(score)에 사용된다.

[출력 파일]
1) app/ai_models/routine_scorer_lgbm.pkl
2) app/ai_models/routine_scorer_encoders.pkl

[중요]
- services/routine_generator/scorer.py 의 feature 구성과 100% 일치
- 이 파일만 실행하면 학습 완료
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

MODEL_PATH = "app/ai_models/routine_scorer_model.pkl"
ENCODER_PATH = "app/ai_models/routine_scorer_encoders.pkl"


# ===============================
# 2. 학습 데이터 로딩
# ===============================
def get_training_data() -> pd.DataFrame:
    """
    루틴 단위 학습 데이터 생성

    routine_score:
    - 완료율 기반 점수 (0~100)
    """
    query = """
    SELECT
        al.id                               AS activity_id,
        u.gender                           AS gender,
        u.goal                             AS goal,
        u.fitness_level                    AS fitness_level,
        latest_ubi.bmi                     AS bmi,
        latest_ubi.body_fat                AS body_fat,
        latest_ubi.skeletal_muscle         AS skeletal_muscle,

        COUNT(adl.id)                      AS total_sets,
        COALESCE(AVG(adl.score), 70)       AS avg_pose_score,
        AVG(adl.reps_done)                 AS avg_reps,

        al.completed_ratio * 100           AS routine_score

    FROM activity_logs al
    JOIN users u ON al.user_id = u.id
    JOIN activity_detail_logs adl ON al.id = adl.activity_id

    LEFT JOIN (
        SELECT DISTINCT ON (user_id)
            user_id,
            bmi,
            body_fat,
            skeletal_muscle
        FROM user_body_info
        ORDER BY user_id, updated_at DESC
    ) latest_ubi ON al.user_id = latest_ubi.user_id

    WHERE
        al.status = 'FINISHED'

    GROUP BY
        al.id,
        u.gender,
        u.goal,
        u.fitness_level,
        latest_ubi.bmi,
        latest_ubi.body_fat,
        latest_ubi.skeletal_muscle,
        al.completed_ratio
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
    print("🔄 Loading routine training data...")
    df = get_training_data()

    if df.empty:
        raise RuntimeError("❌ RoutineScorer 학습 데이터가 없습니다.")

    print(f"✅ Raw rows: {len(df)}")

    # 필수 feature만 결측 제거
    df.dropna(subset=[
        "bmi",
        "body_fat",
        "skeletal_muscle",
        "avg_reps",
    ], inplace=True)

    print(f"✅ After dropna: {len(df)}")

    # ===============================
    # 3-1. 범주형 인코딩
    # ===============================
    categorical_cols = ["gender", "goal"]

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
        "total_sets",
        "avg_pose_score",
        "avg_reps",
    ]

    X = df[FEATURE_COLUMNS]
    y = df["routine_score"]

    print(f"🧠 Feature count: {X.shape[1]} (must be 9)")

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
        n_estimators=500,
        learning_rate=0.03,
        max_depth=6,
        num_leaves=48,
        min_child_samples=20,
        random_state=42,
    )

    print("🤖 Training RoutineScorer model...")
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
    print("🎉 RoutineScorer training pipeline finished successfully.")
