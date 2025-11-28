-- 1. UUID 확장 기능 변경: "pgcrypto" 확장 프로그램 생성 (사용자 요청 반영)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. 외래 키 종속성을 고려하여 모든 테이블을 안전하게 삭제 (초기화)
DROP TABLE IF EXISTS algorithm_config CASCADE;
DROP TABLE IF EXISTS ranking CASCADE;
DROP TABLE IF EXISTS challenge_participation CASCADE;
DROP TABLE IF EXISTS challenges CASCADE;
DROP TABLE IF EXISTS user_routine_progress CASCADE;
DROP TABLE IF EXISTS routine_flow CASCADE;
DROP TABLE IF EXISTS wearable_data CASCADE;
DROP TABLE IF EXISTS pose_analysis CASCADE;
DROP TABLE IF EXISTS activity_detail_logs CASCADE;
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS ai_routine_items CASCADE; -- AI 루틴 상세 테이블 추가
DROP TABLE IF EXISTS ai_recommended_routines CASCADE;
DROP TABLE IF EXISTS routine_items CASCADE;
DROP TABLE IF EXISTS routines CASCADE;
DROP TABLE IF EXISTS exercise CASCADE;
DROP TABLE IF EXISTS payment_history CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS subscription_plans CASCADE;
DROP TABLE IF EXISTS user_body_info CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- 3. 테이블 다시 생성 (기본 값: gen_random_uuid() 적용)

-- 1. USER (회원 정보)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(100),
    phone VARCHAR(20),
    birthdate DATE,
    gender VARCHAR(10),
    goal VARCHAR(50), -- 체지방 감소(FAT_LOSS), 근력 향상(MUSCLE_GAIN), 지구력 증진(ENDURANCE), 기초체력 유지(MAINTAIN)
    fitness_level INT DEFAULT 1, -- 1: 초보, 2: 중급, 3: 고급
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);


-- 2. USER_BODY_INFO (사용자 생체 정보)
CREATE TABLE user_body_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    height_cm NUMERIC(5,2) NOT NULL,
    weight_kg NUMERIC(5,2) NOT NULL,
    body_fat NUMERIC(5,2),
    skeletal_muscle NUMERIC(5,2),
    bmr NUMERIC(6,2),
    visceral_fat_level INT,
    water NUMERIC(5,2),
    bmi NUMERIC(5,2),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. SUBSCRIPTION_PLANS (구독 플랜)
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    description TEXT
);

-- 4. SUBSCRIPTIONS (사용자 구독 내역)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    status VARCHAR(20) NOT NULL,  -- 'PENDING', 'ACTIVE', 'EXPIRED'
    start_date DATE NOT NULL,
    end_date DATE,
    next_billing_date DATE
);

-- 5. PAYMENT_HISTORY (결제 내역)
CREATE TABLE payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    amount NUMERIC(10,2) NOT NULL,
    paid_at TIMESTAMP DEFAULT NOW(),
    payment_method VARCHAR(50),
    refund_status VARCHAR(20)
);

-- 6. EXERCISE (운동 종목)
CREATE TABLE exercise (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    posture VARCHAR(50),
    category_1 VARCHAR(50),  -- 운동 부위(주): 상체(UPPER_BODY), 코어(CORE), 하체(LOWER_BODY), 전신(FULL_BODY)
    category_2 VARCHAR(50),  -- 운동 부위(부): 상체(UPPER_BODY), 코어(CORE), 하체(LOWER_BODY), 전신(FULL_BODY) 없음('0')
    difficulty INT,
    MET NUMERIC(4,2),
    description TEXT,
    thumbnail_url TEXT,
    video_url TEXT
);

-- 7. ROUTINES (표준 루틴)
CREATE TABLE routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- 8. ROUTINE_ITEMS (표준 루틴 구성)
CREATE TABLE routine_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routine_id UUID NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercise(id),
    set_count INT,
    reps INT,
    duration_sec INT,
    rest_sec INT
);

-- 9. AI_RECOMMENDED_ROUTINES (AI 추천 루틴) - **누락된 목표 정보 복원**
CREATE TABLE ai_recommended_routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_type VARCHAR(50) NOT NULL,                 -- 복원된 컬럼
    target_value NUMERIC(10,2) NOT NULL,            -- 복원된 컬럼
    ai_model_type VARCHAR(50),                      -- 복원된 컬럼
    created_at TIMESTAMP DEFAULT NOW(),
    total_time_min NUMERIC(6,2),
    total_calories NUMERIC(8,2)
);

-- 9-1. AI_ROUTINE_ITEMS (AI 추천 루틴 구성 상세) - **누락된 테이블 복원**
CREATE TABLE ai_routine_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_routine_id UUID NOT NULL REFERENCES ai_recommended_routines(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercise(id),
    step_number INT NOT NULL,
    set_count INT,
    reps INT,
    duration_sec INT,
    rest_sec INT
);

-- 10. ACTIVITY_LOGS (운동 기록 요약) - **표준/AI 루틴 FK 분리 복원**
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    standard_routine_id UUID REFERENCES routines(id),     -- 표준 루틴 FK
    ai_routine_id UUID REFERENCES ai_recommended_routines(id), -- AI 루틴 FK
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    cancellation_reason VARCHAR(100) DEFAULT NULL, -- 예: 'TOO_HARD', 'TOO_LONG', 'INJURY', 'INTERRUPTED' 등
    total_time_min NUMERIC(6,2),
    total_calories NUMERIC(10,2)
);

-- 11. ACTIVITY_DETAIL_LOGS (운동 상세 기록)
CREATE TABLE activity_detail_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID NOT NULL REFERENCES activity_logs(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercise(id),
    set_number INT NOT NULL,
    reps_done INT,
    score NUMERIC(5,2)
);

-- 12. POSE_ANALYSIS (AI 자세 분석 결과)
CREATE TABLE pose_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercise(id),
    frame_file_name TEXT,
    angles_json JSONB,
    issues_json JSONB,
    score NUMERIC(5,2),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 13. WEARABLE_DATA (웨어러블 데이터)
CREATE TABLE wearable_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    steps INT,
    heart_rate INT,
    sleep_minutes INT,
    calories_active NUMERIC(10,2),
    recorded_at TIMESTAMP,
    raw_json JSONB
);

-- 14. ROUTINE_FLOW (운동 안내 단계)
CREATE TABLE routine_flow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routine_id UUID NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercise(id),
    step_number INT NOT NULL,
    set_count INT,
    reps INT,
    duration_sec INT,
    rest_sec INT,
    tts_script TEXT,
    guidance_text TEXT
);

-- 15. USER_ROUTINE_PROGRESS (사용자 운동 진행 상태)
CREATE TABLE user_routine_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    routine_id UUID NOT NULL REFERENCES routines(id),
    current_step INT,
    current_set INT,
    status VARCHAR(30), -- PENDING(추천은 받았으나 시작 전), IN_PROGRESS(운동 중), CANCELED(중도 포기/취소), FINISHED(루틴 완료)
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 16. CHALLENGES (챌린지)
CREATE TABLE challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100),
    period_days INT,
    reward_type VARCHAR(50),
    description TEXT
);

-- 17. CHALLENGE_PARTICIPATION
CREATE TABLE challenge_participation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    progress_percent NUMERIC(5,2),
    score NUMERIC(10,2)
);

-- 18. RANKING (랭킹 시스템)
CREATE TABLE ranking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score NUMERIC(10,2),
    weekly_rank INT
);

-- 19. ALGORITHM_CONFIG (알고리즘 설정)
CREATE TABLE algorithm_config (
    config_name VARCHAR(100) PRIMARY KEY, -- 설정 항목 이름 (예: 'MUSCLE_GAIN_WEIGHTS', 'DIFFICULTY_LEVEL_1')
    config_type VARCHAR(50) NOT NULL,     -- 설정 유형 (예: 'SCORING_WEIGHT', 'DIFFICULTY_PARAM')
    data JSONB NOT NULL,                  -- 세부 설정 값을 JSON 형태로 저장 ({"set_count": 3, "reps_min": 8, "reps_max": 10, "rest_sec": 60})
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

exercise 데이터 입력    
INSERT INTO exercise (name, type, posture, category_1, category_2, difficulty, MET)
values ('스탠딩 사이드 크런치', '근력', '선 자세', '코어', '하체', 3, 4),
('스탠딩 니업', '유산소', '선 자세', '상체', '하체', 3, 3.8),
('버피 테스트', '근력/유산소', '선 자세', '전신', '0', 5, 8),
('스텝 포워드 다이나믹 런지', '근력/유산소', '선 자세', '하체', '0', 4, 4),
('스텝 백워드 다이나믹 런지', '근력/유산소', '선 자세', '하체', '0', 4, 4),
('사이드 런지', '근력/유산소', '선 자세', '하체', '0', 5, 5),
('크로스 런지', '근력/유산소', '선 자세', '하체', '코어', 4, 3.8),
('굿모닝', '근력', '선 자세', '하체', '0', 5, 5),
('라잉 레그 레이즈', '근력', '누운 자세', '코어', '하체', 4, 4),
('크런치', '근력', '누운 자세', '코어', '0', 4, 4.5),
('바이시클 크런치', '근력/유산소', '누운 자세', '코어', '하체', 5, 5),
('시저 크로스', '근력/유산소', '누운 자세', '코어', '하체', 4, 4.5),
('힙 쓰러스트', '근력', '누운 자세', '하체', '코어', 3, 3.5),
('플랭크', '근력', '엎드린 자세', '코어', '하체', 5, 8),
('푸시업', '근력', '엎드린 자세', '상체', '코어', 4, 6),
('니 푸쉬업', '근력', '엎드린 자세', '상체', '코어', 3, 5),
('와이 엑서사이즈', '근력', '엎드린 자세', '상체', '코어', 3, 4.5)