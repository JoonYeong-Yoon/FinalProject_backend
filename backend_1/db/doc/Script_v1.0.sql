-- 1. UUID 확장 기능 변경: "pgcrypto" 확장 프로그램 생성
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
DROP TABLE IF EXISTS ai_routine_items CASCADE;
DROP TABLE IF EXISTS ai_recommended_routines CASCADE;
DROP TABLE IF EXISTS routine_items CASCADE;
DROP TABLE IF EXISTS routines CASCADE;
DROP TABLE IF EXISTS exercise CASCADE;
DROP TABLE IF EXISTS payment_history CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS subscription_plans CASCADE;
DROP TABLE IF EXISTS user_body_info CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- 3. 테이블 다시 생성

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
    user_id UUID PRIMARY KEY NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
    status VARCHAR(20) NOT NULL, -- 'PENDING', 'ACTIVE', 'EXPIRED'
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
    -- 🚨 'posture' 컬럼명에서 숨겨진 문자(BOM) 제거
    posture VARCHAR(50), 
    category_1 VARCHAR(50),  -- 운동 부위(주): 상체(UPPER_BODY), 코어(CORE), 하체(LOWER_BODY), 전신(FULL_BODY)
    category_2 VARCHAR(50),  -- 운동 부위(부): 상체(UPPER_BODY), 코어(CORE), 하체(LOWER_BODY), 전신(FULL_BODY), 없음('0')
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

-- 9. AI_RECOMMENDED_ROUTINES (AI 추천 루틴)
CREATE TABLE ai_recommended_routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_type VARCHAR(50) NOT NULL,
    target_value NUMERIC(10,2) NOT NULL,
    ai_model_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    total_time_min NUMERIC(6,2),
    total_calories NUMERIC(8,2)
);

-- 9-1. AI_ROUTINE_ITEMS (AI 추천 루틴 구성 상세)
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

-- 10. ACTIVITY_LOGS (운동 기록 요약)
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    standard_routine_id UUID REFERENCES routines(id),
    ai_routine_id UUID REFERENCES ai_recommended_routines(id),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    cancellation_reason VARCHAR(100) DEFAULT NULL,
    injury_area VARCHAR(50) DEFAULT NULL,
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
    routine_id UUID REFERENCES routines(id),
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
    config_name VARCHAR(100) PRIMARY KEY,
    config_type VARCHAR(50) NOT NULL, -- 🚨 NOT NULL 오류 수정
    data JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------
-- 4. 테스트 데이터 삽입
-- ------------------------------------

-- EXERCISE 데이터 입력 (🚨 난이도 1, 2 CORE 운동 보강)
INSERT INTO exercise (name, type, posture, category_1, category_2, difficulty, MET)
VALUES
('스탠딩 사이드 크런치', '근력', '선 자세', 'CORE', 'LOWER_BODY', 1, 3.5), -- D1로 조정
('스탠딩 니업', '유산소', '선 자세', 'UPPER_BODY', 'LOWER_BODY', 3, 3.8),
('버피 테스트', '근력/유산소', '선 자세', 'FULL_BODY', '0', 5, 8),
('스텝 포워드 다이나믹 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 4, 4),
('스텝 백워드 다이나믹 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 4, 4),
('사이드 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 5, 5),
('크로스 런지', '근력/유산소', '선 자세', 'LOWER_BODY', 'CORE', 4, 3.8),
('굿모닝', '근력', '선 자세', 'LOWER_BODY', '0', 5, 5),
('라잉 레그 레이즈', '근력', '누운 자세', 'CORE', 'LOWER_BODY', 4, 4),
('크런치', '근력', '누운 자세', 'CORE', '0', 2, 4.5), -- D2로 조정
('바이시클 크런치', '근력/유산소', '누운 자세', 'CORE', 'LOWER_BODY', 5, 5),
('시저 크로스', '근력/유산소', '누운 자세', 'CORE', 'LOWER_BODY', 4, 4.5),
('힙 쓰러스트', '근력', '누운 자세', 'LOWER_BODY', 'CORE', 3, 3.5),
('플랭크', '근력', '엎드린 자세', 'CORE', 'LOWER_BODY', 2, 5.0), -- D2로 조정
('푸시업', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 4, 6),
('니 푸쉬업', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 3, 5),
('와이 엑서사이즈', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 3, 4.5);


-- ALGORITHM_CONFIG (알고리즘 설정)
INSERT INTO algorithm_config (config_name, config_type, data, description) VALUES
('DIFFICULTY_LEVEL_1', 'DIFFICULTY_PARAM', '{"set_count": 3, "reps_min": 8, "reps_max": 10, "duration_sec": 30, "rest_sec": 60}', '초보자 (레벨 1) 루틴 파라미터'),
('DIFFICULTY_LEVEL_2', 'DIFFICULTY_PARAM', '{"set_count": 4, "reps_min": 10, "reps_max": 12, "duration_sec": 45, "rest_sec": 45}', '중급자 (레벨 2) 루틴 파라미터'),
('DIFFICULTY_LEVEL_3', 'DIFFICULTY_PARAM', '{"set_count": 5, "reps_min": 12, "reps_max": 15, "duration_sec": 60, "rest_sec": 30}', '고급자 (레벨 3) 루틴 파라미터'),
('MUSCLE_GAIN_WEIGHTS', 'SCORING_WEIGHT', '{"pose_score": 45, "rep_achieved": 30, "routine_complete": 15, "body_change": 10}', '근력 향상 목표 달성 평가 가중치'),
('FAT_LOSS_WEIGHTS', 'SCORING_WEIGHT', '{"calorie_burn": 40, "routine_complete": 30, "body_change": 20, "activity_frequency": 10}', '체지방 감소 목표 달성 평가 가중치'),
('ENDURANCE_WEIGHTS', 'SCORING_WEIGHT', '{"routine_complete": 40, "time_achieved": 30, "heart_rate_zone": 20, "rest_efficiency": 10}', '지구력 증진 목표 달성 평가 가중치'),
('MAINTAIN_WEIGHTS', 'SCORING_WEIGHT', '{"activity_frequency": 40, "lifestyle_steps": 30, "routine_complete": 20, "body_stability": 10}', '기초 체력 유지 목표 달성 평가 가중치');

-- SUBSCRIPTION_PLANS (구독 플랜) 기본 구독 플랜 설정
INSERT INTO subscription_plans (name, price, description) VALUES
('Basic', 9900.00, '기본 AI 자세 인식 및 표준 루틴 이용'),
('Pro', 19900.00, '개인 맞춤형 AI 루틴 및 상세 기록 제공'),
('Premium', 29900.00, '최고 수준의 맞춤 관리 및 전담 AI 트레이너 채팅을 이용할 수 있습니다.');

-- ROUTINES, ROUTINE_ITEMS, ROUTINE_FLOW (표준 루틴 생성)
WITH new_routine AS (
    INSERT INTO routines (name, description) VALUES
    ('초보자 전신 근력 강화 (30분)', 'AI 추천 시스템 미작동 시 제공되는 기본 전신 근력 루틴입니다.')
    RETURNING id
),
selected_exercises AS (
    SELECT id, name FROM exercise WHERE name IN ('푸시업', '힙 쓰러스트', '플랭크')
),
routine_definition AS (
    SELECT
        (SELECT id FROM new_routine) AS routine_id,
        (SELECT id FROM selected_exercises WHERE name = '푸시업') AS pushup_id,
        (SELECT id FROM selected_exercises WHERE name = '힙 쓰러스트') AS hip_thrust_id,
        (SELECT id FROM selected_exercises WHERE name = '플랭크') AS plank_id
)
INSERT INTO routine_flow (routine_id, exercise_id, step_number, set_count, reps, duration_sec, rest_sec, tts_script, guidance_text)
SELECT 
    rd.routine_id, 
    rd.pushup_id, 
    1, 
    3, 
    10,          -- reps (INT)
    NULL::INT,   -- duration_sec (NULL을 INT로 명시적 캐스팅)
    60, 
    '첫 번째 운동, 푸시업 10회 3세트를 시작합니다. 가슴이 바닥에 닿을 정도로 내려가세요.', 
    '팔꿈치를 벌리지 않고 몸에 붙여 수행하세요. 60초 휴식 후 다음 세트.' 
FROM routine_definition rd
UNION ALL
SELECT 
    rd.routine_id, 
    rd.hip_thrust_id, 
    2, 
    3, 
    15,          -- reps (INT)
    NULL::INT,   -- duration_sec (NULL을 INT로 명시적 캐스팅)
    45, 
    '두 번째 운동, 힙 쓰러스트 15회 3세트입니다. 엉덩이를 끝까지 수축하여 올리세요.', 
    '허리가 과도하게 젖혀지지 않도록 코어에 힘을 주세요. 45초 휴식 후 다음 세트.' 
FROM routine_definition rd
UNION ALL
SELECT 
    rd.routine_id, 
    rd.plank_id, 
    3, 
    3, 
    NULL::INT,   -- reps (NULL을 INT로 명시적 캐스팅)
    60,          -- duration_sec (INT)
    30, 
    '마지막 운동, 플랭크 60초 3세트입니다. 코어에 집중하고 몸을 일직선으로 유지하세요.', 
    '엉덩이가 처지거나 너무 솟지 않도록 주의하세요. 30초 휴식 후 다음 세트.' 
FROM routine_definition rd;

-- ROUTINE_FLOW 데이터를 ROUTINE_ITEMS에 복사
INSERT INTO routine_items (routine_id, exercise_id, set_count, reps, duration_sec, rest_sec)
SELECT routine_id, exercise_id, set_count, reps, duration_sec, rest_sec FROM routine_flow;

-- 테스트 사용자 데이터 삽입 (기존 사용자들)
INSERT INTO users (email, password_hash, name, birthdate, gender, goal, fitness_level) VALUES
('kimchobо@example.com', 'hashed_password_1', '김초보', '1995-03-15', 'M', 'MUSCLE_GAIN', 1),
('parkjoong@example.com', 'hashed_password_2', '박중급', '1990-08-22', 'F', 'FAT_LOSS', 2),
('leeadvanced@example.com', 'hashed_password_3', '이숙련', '2000-01-01', 'M', 'ENDURANCE', 3)
ON CONFLICT (email) DO UPDATE SET fitness_level = EXCLUDED.fitness_level;

-- 🚨 API 테스트에 사용되는 특정 사용자 데이터 삽입 (ffdadcd5-0cca-423e-8780-7848cda3c700)
INSERT INTO users (id, email, password_hash, name, birthdate, gender, goal, fitness_level)
VALUES ('ffdadcd5-0cca-423e-8780-7848cda3c700', 'test@example.com', 'hashed_pass', '테스트유저', '1990-01-01', 'M', 'MUSCLE_GAIN', 1)
ON CONFLICT (id) DO UPDATE 
SET 
    fitness_level = EXCLUDED.fitness_level, 
    email = EXCLUDED.email, 
    birthdate = EXCLUDED.birthdate, 
    gender = EXCLUDED.gender,
    goal = EXCLUDED.goal;

-- 각 사용자의 체성분 정보 삽입
INSERT INTO user_body_info (user_id, height_cm, weight_kg, bmi, bmr)
SELECT id, 175.0, 70.0, 22.86, 1650.0 FROM users WHERE name = '김초보'
UNION ALL
SELECT id, 165.0, 68.0, 24.98, 1450.0 FROM users WHERE name = '박중급'
UNION ALL
SELECT id, 180.0, 75.0, 23.15, 1800.0 FROM users WHERE name = '이숙련'
UNION ALL
-- 🚨 API 테스트 유저의 신체 정보 삽입
SELECT id, 178.0, 75.0, 23.7, 1800.0 FROM users WHERE id = 'ffdadcd5-0cca-423e-8780-7848cda3c700'
ON CONFLICT (user_id) DO UPDATE 
SET 
    height_cm = EXCLUDED.height_cm, 
    weight_kg = EXCLUDED.weight_kg, 
    bmr = EXCLUDED.bmr;

-- USER_BODY_INFO 테이블의 체성분 데이터 보강
UPDATE user_body_info
SET body_fat = 22.5, skeletal_muscle = 33.0, visceral_fat_level = 9, water = 55.0
WHERE user_id IN (SELECT id FROM users WHERE name = '김초보' OR id = 'ffdadcd5-0cca-423e-8780-7848cda3c700');

UPDATE user_body_info
SET body_fat = 30.1, skeletal_muscle = 27.5, visceral_fat_level = 8, water = 52.0
WHERE user_id IN (SELECT id FROM users WHERE name = '박중급');

UPDATE user_body_info
SET body_fat = 15.0, skeletal_muscle = 39.5, visceral_fat_level = 6, water = 60.0
WHERE user_id IN (SELECT id FROM users WHERE name = '이숙련');


