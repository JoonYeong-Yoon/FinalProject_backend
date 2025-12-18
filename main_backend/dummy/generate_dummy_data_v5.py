"""
개요:
AI 모델 학습을 위해 '유연한 논리 패턴(Goal과 Level 분리)'이 적용된 가상 사용자 및 운동 기록을 생성.
**Decimal 타입과 Float 타입 간의 연산 오류가 최종적으로 수정된 버전.**

주요 특징:
1. SQL 스키마에 UNIQUE 제약 조건이 설정되었다고 가정하고, 순수 DML(데이터 삽입)만 수행.
2. with 구문을 사용한 DB 연결 및 트랜잭션 관리 강화 (Commit 안정성 확보)
3. 논리적 AI 학습용 데이터 생성 및 최종 검증 로직 포함
"""

import psycopg2
import uuid
import random
import time
import os
from datetime import datetime, timedelta
from faker import Faker

# Faker 설정
fake = Faker('ko_KR')

# DB 연결 정보 (우선순위: localhost -> db 컨테이너)
DB_CONFIGS = [
    {"host": "localhost", "port": "5432", "user": "postgres", "password": "postgres", "dbname": "home_training_db"},
    {"host": "db", "port": "5432", "user": "postgres", "password": "postgres", "dbname": "home_training_db"}
]

# API 테스트 유저의 ID (삭제 방지용 및 참조용)
# ⚠️ 이 ID는 DB에 고정 사용자로 존재해야 합니다.
TEST_USER_ID = 'ffdadcd5-0cca-423e-8780-7848cda3c700'

# ---------------------------------------------------------
# 1. 유연성 강화 정의 및 DB 연결
# ---------------------------------------------------------
FITNESS_LEVELS = [1, 2, 3] # 1: 초급, 2: 중급, 3: 고급
GOAL_CHOICES = ['FAT_LOSS', 'MUSCLE_GAIN', 'MAINTAIN', 'ENDURANCE']

def get_db_connection():
    """DB 연결을 시도하고 성공한 커넥션을 반환합니다."""
    for config in DB_CONFIGS:
        try:
            conn = psycopg2.connect(**config)
            conn.autocommit = False # 트랜잭션 명시적 관리
            print(f"✅ DB 연결 성공! ({config['host']})")
            return conn
        except psycopg2.OperationalError:
            continue
    
    print("❌ 모든 DB 연결 시도 실패. Docker 컨테이너가 실행 중인지 확인하세요.")
    return None

def wait_for_db():
    """DB가 준비될 때까지 기다립니다."""
    max_retries = 10
    for i in range(max_retries):
        conn = get_db_connection()
        if conn:
            return conn
        print(f"⏳ DB 대기 중... ({i+1}/{max_retries})")
        time.sleep(3)
    raise Exception("DB 연결 시간 초과")

# ---------------------------------------------------------
# 2. 참조 데이터 및 고정 사용자 삽입 (순수 DML)
# ---------------------------------------------------------
def insert_reference_data(cursor):
    """운동 종목, AI 설정, 표준 루틴, 고정 테스트 사용자를 삽입합니다."""
    print("📋 참조 데이터(Exercise, Config, Standard Users) 삽입/갱신 중...")
    
    # 2.1. EXERCISE 데이터 삽입
    # name에 UNIQUE 제약 조건이 설정되어 있다고 가정하고, VALUES 목록을 쉼표로 연결
    exercise_sql = """
    INSERT INTO exercise (name, type, posture, category_1, category_2, difficulty, MET)
    VALUES
    ('스탠딩 사이드 크런치', '근력', '선 자세', 'CORE', 'LOWER_BODY', 1, 3.5),
    ('스탠딩 니업', '유산소', '선 자세', 'UPPER_BODY', 'LOWER_BODY', 3, 3.8),
    ('버피 테스트', '근력/유산소', '선 자세', 'FULL_BODY', '0', 5, 8),
    ('스텝 포워드 다이나믹 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 4, 4),
    ('스텝 백워드 다이나믹 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 4, 4),
    ('사이드 런지', '근력/유산소', '선 자세', 'LOWER_BODY', '0', 5, 5),
    ('크로스 런지', '근력/유산소', '선 자세', 'LOWER_BODY', 'CORE', 4, 3.8),
    ('굿모닝', '근력', '선 자세', 'LOWER_BODY', '0', 5, 5),
    ('라잉 레그 레이즈', '근력', '누운 자세', 'CORE', 'LOWER_BODY', 4, 4),
    ('크런치', '근력', '누운 자세', 'CORE', '0', 2, 4.5),
    ('바이시클 크런치', '근력/유산소', '누운 자세', 'CORE', 'LOWER_BODY', 5, 5),
    ('시저 크로스', '근력/유산소', '누운 자세', 'CORE', 'LOWER_BODY', 4, 4.5),
    ('힙 쓰러스트', '근력', '누운 자세', 'LOWER_BODY', 'CORE', 3, 3.5),
    ('플랭크', '근력', '엎드린 자세', 'CORE', 'LOWER_BODY', 2, 5.0),
    ('푸시업', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 4, 6),
    ('니 푸쉬업', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 3, 5),
    ('와이 엑서사이즈', '근력', '엎드린 자세', 'UPPER_BODY', 'CORE', 3, 4.5)
    ON CONFLICT (name) DO NOTHING;
    """
    cursor.execute(exercise_sql)

    # 2.2. ALGORITHM_CONFIG 및 SUBSCRIPTION_PLANS 삽입/갱신
    # config_name과 name에 UNIQUE 제약 조건이 설정되어 있다고 가정하고, VALUES 목록을 쉼표로 연결
    config_sql = """
    -- ALGORITHM_CONFIG (알고리즘 설정)
    INSERT INTO algorithm_config (config_name, config_type, data, description) VALUES
    ('DIFFICULTY_LEVEL_1', 'DIFFICULTY_PARAM', '{"set_count": 3, "reps_min": 8, "reps_max": 10, "duration_sec": 30, "rest_sec": 60}', '초보자 (레벨 1) 루틴 파라미터'),
    ('DIFFICULTY_LEVEL_2', 'DIFFICULTY_PARAM', '{"set_count": 4, "reps_min": 10, "reps_max": 12, "duration_sec": 45, "rest_sec": 45}', '중급자 (레벨 2) 루틴 파라미터'),
    ('DIFFICULTY_LEVEL_3', 'DIFFICULTY_PARAM', '{"set_count": 5, "reps_min": 12, "reps_max": 15, "duration_sec": 60, "rest_sec": 30}', '고급자 (레벨 3) 루틴 파라미터'),
    ('MUSCLE_GAIN_WEIGHTS', 'SCORING_WEIGHT', '{"pose_score": 45, "rep_achieved": 30, "routine_complete": 15, "body_change": 10}', '근력 향상 목표 달성 평가 가중치'),
    ('FAT_LOSS_WEIGHTS', 'SCORING_WEIGHT', '{"calorie_burn": 40, "routine_complete": 30, "body_change": 20, "activity_frequency": 10}', '체지방 감소 목표 달성 평가 가중치'),
    ('ENDURANCE_WEIGHTS', 'SCORING_WEIGHT', '{"routine_complete": 40, "time_achieved": 30, "heart_rate_zone": 20, "rest_efficiency": 10}', '지구력 증진 목표 달성 평가 가중치'),
    ('MAINTAIN_WEIGHTS', 'SCORING_WEIGHT', '{"activity_frequency": 40, "lifestyle_steps": 30, "routine_complete": 20, "body_stability": 10}', '기초 체력 유지 목표 달성 평가 가중치')
    ON CONFLICT (config_name) DO UPDATE SET data = EXCLUDED.data, description = EXCLUDED.description;

    -- SUBSCRIPTION_PLANS (구독 플랜) 기본 구독 플랜 설정
    INSERT INTO subscription_plans (name, price, description) VALUES
    ('Basic', 9900.00, '기본 AI 자세 인식 및 표준 루틴 이용'),
    ('Pro', 19900.00, '개인 맞춤형 AI 루틴 및 상세 기록 제공'),
    ('Premium', 29900.00, '최고 수준의 맞춤 관리 및 전담 AI 트레이너 채팅을 이용할 수 있습니다.')
    ON CONFLICT (name) DO UPDATE SET price = EXCLUDED.price, description = EXCLUDED.description;
    """
    cursor.execute(config_sql)
    
    # 2.3. 표준 ROUTINES 데이터 삽입 (SELECT + UNION ALL 구문 사용 - 유효)
    routine_sql = """
    -- ROUTINES, ROUTINE_ITEMS, ROUTINE_FLOW (표준 루틴 생성)
    WITH new_routine AS (
        INSERT INTO routines (name, description) VALUES
        ('초보자 전신 근력 강화 (30분)', 'AI 추천 시스템 미작동 시 제공되는 기본 전신 근력 루틴입니다.')
        ON CONFLICT (name) DO NOTHING 
        RETURNING id
    ),
    selected_exercises AS (
        SELECT id, name FROM exercise WHERE name IN ('푸시업', '힙 쓰러스트', '플랭크')
    ),
    routine_definition AS (
        SELECT
            (SELECT id FROM new_routine LIMIT 1) AS routine_id,
            (SELECT id FROM selected_exercises WHERE name = '푸시업') AS pushup_id,
            (SELECT id FROM selected_exercises WHERE name = '힙 쓰러스트') AS hip_thrust_id,
            (SELECT id FROM selected_exercises WHERE name = '플랭크') AS plank_id
    )
    -- 첫 번째 INSERT: ROUTINE_FLOW
    INSERT INTO routine_flow (routine_id, exercise_id, step_number, set_count, reps, duration_sec, rest_sec, tts_script, guidance_text)
    SELECT 
        rd.routine_id, 
        rd.pushup_id, 
        1, 
        3, 
        10,          
        NULL::INT,
        60, 
        '첫 번째 운동, 푸시업 10회 3세트를 시작합니다. 가슴이 바닥에 닿을 정도로 내려가세요.', 
        '팔꿈치를 벌리지 않고 몸에 붙여 수행하세요. 60초 휴식 후 다음 세트.' 
    FROM routine_definition rd
    WHERE rd.routine_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM routine_flow WHERE routine_id = rd.routine_id AND step_number = 1) 
    UNION ALL
    SELECT 
        rd.routine_id, 
        rd.hip_thrust_id, 
        2, 
        3, 
        15,          
        NULL::INT,   
        45, 
        '두 번째 운동, 힙 쓰러스트 15회 3세트입니다. 엉덩이를 끝까지 수축하여 올리세요.', 
        '허리가 과도하게 젖혀지지 않도록 코어에 힘을 주세요. 45초 휴식 후 다음 세트.' 
    FROM routine_definition rd
    WHERE rd.routine_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM routine_flow WHERE routine_id = rd.routine_id AND step_number = 2)
    UNION ALL
    SELECT 
        rd.routine_id, 
        rd.plank_id, 
        3, 
        3, 
        NULL::INT,   
        60,          
        30, 
        '마지막 운동, 플랭크 60초 3세트입니다. 코어에 집중하고 몸을 일직선으로 유지하세요.', 
        '엉덩이가 처지거나 너무 솟지 않도록 주의하세요. 30초 휴식 후 다음 세트.' 
    FROM routine_definition rd
    WHERE rd.routine_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM routine_flow WHERE routine_id = rd.routine_id AND step_number = 3);
    
    -- 두 번째 INSERT: ROUTINE_FLOW 데이터를 ROUTINE_ITEMS에 복사 (중복 방지 로직 필요)
    INSERT INTO routine_items (routine_id, exercise_id, set_count, reps, duration_sec, rest_sec)
    SELECT rf.routine_id, rf.exercise_id, rf.set_count, rf.reps, rf.duration_sec, rf.rest_sec
    FROM routine_flow rf
    LEFT JOIN routine_items ri ON ri.routine_id = rf.routine_id AND ri.exercise_id = rf.exercise_id
    WHERE ri.routine_id IS NULL; 
    """
    cursor.execute(routine_sql)

    # 2.4. 고정 사용자 및 체성분 삽입/갱신
    static_users_sql = f"""
    -- 테스트 사용자 데이터 삽입 (기존 사용자들)
    INSERT INTO users (email, password_hash, name, birthdate, gender, goal, fitness_level) VALUES
    ('kimchobo@example.com', 'hashed_password_1', '김초보', '1995-03-15', 'M', 'MUSCLE_GAIN', 1),
    ('parkjoong@example.com', 'hashed_password_2', '박중급', '1990-08-22', 'F', 'FAT_LOSS', 2),
    ('leeadvanced@example.com', 'hashed_password_3', '이숙련', '2000-01-01', 'M', 'ENDURANCE', 3)
    ON CONFLICT (email) DO UPDATE SET fitness_level = EXCLUDED.fitness_level, goal = EXCLUDED.goal;

    -- 🚨 API 테스트에 사용되는 특정 사용자 데이터 삽입 ({TEST_USER_ID})
    INSERT INTO users (id, email, password_hash, name, birthdate, gender, goal, fitness_level)
    VALUES ('{TEST_USER_ID}', 'test@example.com', 'hashed_pass', '테스트유저', '1990-01-01', 'M', 'MUSCLE_GAIN', 1)
    ON CONFLICT (id) DO UPDATE 
    SET 
        fitness_level = EXCLUDED.fitness_level, 
        email = EXCLUDED.email, 
        birthdate = EXCLUDED.birthdate, 
        gender = EXCLUDED.gender,
        goal = EXCLUDED.goal;

    -- 각 사용자의 체성분 정보 삽입 (UNION ALL 마지막에 ON CONFLICT)
    INSERT INTO user_body_info (user_id, height_cm, weight_kg, bmi, bmr)
    SELECT id, 175.0, 70.0, 22.86, 1650.0 FROM users WHERE name = '김초보'
    UNION ALL
    SELECT id, 165.0, 68.0, 24.98, 1450.0 FROM users WHERE name = '박중급'
    UNION ALL
    SELECT id, 180.0, 75.0, 23.15, 1800.0 FROM users WHERE name = '이숙련'
    UNION ALL
    -- 🚨 API 테스트 유저의 신체 정보 삽입
    SELECT id, 178.0, 75.0, 23.7, 1800.0 FROM users WHERE id = '{TEST_USER_ID}'
    ON CONFLICT (user_id) DO UPDATE SET weight_kg = EXCLUDED.weight_kg;

    -- USER_BODY_INFO 테이블의 체성분 데이터 보강 (UPDATE)
    UPDATE user_body_info
    SET body_fat = 22.5, skeletal_muscle = 33.0, visceral_fat_level = 9, water = 55.0
    WHERE user_id IN (SELECT id FROM users WHERE name = '김초보' OR id = '{TEST_USER_ID}');

    UPDATE user_body_info
    SET body_fat = 30.1, skeletal_muscle = 27.5, visceral_fat_level = 8, water = 52.0
    WHERE user_id IN (SELECT id FROM users WHERE name = '박중급');

    UPDATE user_body_info
    SET body_fat = 15.0, skeletal_muscle = 39.5, visceral_fat_level = 6, water = 60.0
    WHERE user_id IN (SELECT id FROM users WHERE name = '이숙련');
    """
    cursor.execute(static_users_sql)
    print("✅ 참조 데이터 삽입/갱신 완료.")


# ---------------------------------------------------------
# 3. 데이터 초기화 및 기초 데이터 로드 (이 부분은 변경 없음)
# ---------------------------------------------------------
def clean_dynamic_data(cursor):
    """테스트 유저를 제외한 모든 동적 데이터를 삭제합니다."""
    print("🧹 기존 동적 더미 데이터 삭제 중...")
    try:
        # 동적 데이터 삭제 (로그, AI 추천 기록)
        cursor.execute("DELETE FROM activity_detail_logs")
        cursor.execute("DELETE FROM activity_logs")
        # AI 루틴 관련 테이블도 삭제 대상에 포함 (AI 루틴이 없으면 데이터 테스트가 불가능)
        cursor.execute("DELETE FROM ai_routine_items") 
        cursor.execute("DELETE FROM ai_recommended_routines") 
        
        # 더미 사용자 체성분 및 사용자 삭제 (고정 테스트 유저 제외)
        cursor.execute(f"DELETE FROM user_body_info WHERE user_id NOT IN ('{TEST_USER_ID}') AND user_id NOT IN (SELECT id FROM users WHERE email IN ('kimchobo@example.com', 'parkjoong@example.com', 'leeadvanced@example.com'))")
        cursor.execute(f"DELETE FROM users WHERE id NOT IN ('{TEST_USER_ID}') AND email NOT IN ('kimchobo@example.com', 'parkjoong@example.com', 'leeadvanced@example.com')")
        
        print("✨ 동적 데이터 초기화 완료.")
    except Exception as e:
        # 이 단계에서 오류가 나면 스키마 문제일 가능성이 높으므로 치명적이지 않다고 판단
        print(f"⚠️ 데이터 초기화 중 오류 발생: {e}")

def get_exercises(cursor):
    """exercise 테이블에서 기본 운동 리스트를 가져옵니다."""
    cursor.execute("SELECT id, name, difficulty, type, category_1 FROM exercise")
    return cursor.fetchall()

# ---------------------------------------------------------
# 4. 유연한 사용자 생성 로직 (변경 없음)
# ---------------------------------------------------------
def create_users_with_flexible_logic(cursor, count=100):
    """AI 학습을 위한 Level 및 Goal이 분리된 사용자를 생성하고 체성분 데이터를 삽입합니다."""
    users = []
    print(f"👥 사용자 {count}명 생성 시작 (Level/Goal 분리 적용)...")

    for _ in range(count):
        user_id = str(uuid.uuid4())
        gender = random.choice(['M', 'F'])
        name = fake.name()
        email = fake.unique.email()
        
        # 1. Level과 Goal을 독립적으로 선택
        level = random.choice(FITNESS_LEVELS)
        goal = random.choice(GOAL_CHOICES)
        
        # 2. 신체 스펙 생성
        height = random.uniform(160, 185)
        weight = (height - 100) * 0.95 + random.uniform(-5, 5) 
        
        # 3. Level과 Goal 조합에 따른 유연한 체성분 설정
        base_muscle = 25 + (level * 5)
        skeletal_muscle = random.uniform(base_muscle - 3, base_muscle + 5)
        
        if goal == 'FAT_LOSS':
            body_fat = random.uniform(25, 38)
            weight *= random.uniform(1.1, 1.25) 
        elif goal == 'MUSCLE_GAIN':
            skeletal_muscle = random.uniform(base_muscle + 5, base_muscle + 10)
            body_fat = random.uniform(15, 25)
            weight *= random.uniform(1.15, 1.3)
        elif goal == 'ENDURANCE':
            body_fat = random.uniform(8, 15)
            skeletal_muscle = random.uniform(base_muscle - 5, base_muscle + 3)
        else: # MAINTAIN
            body_fat = random.uniform(15, 25)

        age = random.randint(20, 40)
        birthdate = datetime.now() - timedelta(days=age*365)
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == 'M' else -161)
        bmi = weight / ((height/100)**2)
        visceral_fat_level = random.randint(5, 15)

        # DB 저장 (users 테이블)
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, name, birthdate, gender, goal, fitness_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING 
        """, (user_id, email, "hash", name, birthdate, gender, goal, level))

        # DB 저장 (user_body_info 테이블)
        cursor.execute("""
            INSERT INTO user_body_info (user_id, height_cm, weight_kg, body_fat, skeletal_muscle, bmr, bmi, visceral_fat_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET weight_kg = EXCLUDED.weight_kg 
        """, (user_id, height, weight, body_fat, skeletal_muscle, bmr, bmi, visceral_fat_level))

        users.append({
            'id': user_id, 
            'level': level, 
            'goal': goal,
            'muscle': float(skeletal_muscle),
            'fat': float(body_fat)
        })
    
    # 고정 사용자 목록 추가 (로그 생성을 위해)
    cursor.execute("SELECT id, fitness_level, goal FROM users WHERE id = %s OR email IN ('kimchobo@example.com', 'parkjoong@example.com', 'leeadvanced@example.com')", (TEST_USER_ID,))
    
    # 고정 사용자 목록의 체성분 정보를 가져와서 float로 변환하여 users 리스트에 추가
    for user_row in cursor.fetchall():
        user_id = user_row[0]
        cursor.execute("SELECT body_fat, skeletal_muscle FROM user_body_info WHERE user_id = %s", (user_id,))
        body_info = cursor.fetchone()
        
        users.append({
            'id': user_id,
            'level': user_row[1],
            'goal': user_row[2],
            # DB에서 가져온 Decimal 타입을 float으로 변환하여 저장
            'muscle': float(body_info[1]) if body_info and body_info[1] is not None else 30.0,
            'fat': float(body_info[0]) if body_info and body_info[0] is not None else 25.0
        })

    print(f"✅ 총 {len(users)}명의 사용자 객체 생성 완료 (더미 + 고정 사용자).")
    return users

# ---------------------------------------------------------
# 5. 논리적 운동 기록 생성 (Decimal to Float 변환 후 연산)
# ---------------------------------------------------------
def create_logical_activity_logs(cursor, users, exercises):
    """사용자 스펙에 따른 논리적인 운동 기록(Reps, Score)을 생성하고 activity_logs.score를 기록합니다."""
    print("🏋️ 논리적 운동 기록 생성 중 (Level 및 Goal 기반 Reps 반영)...")
    
    start_date = datetime.now() - timedelta(days=60)
    total_detail_logs = 0
    total_activity_logs = 0
    total_ai_items = 0
    
    for user in users:
        
        try:
            current_fat = float(user['fat'])
            current_muscle = float(user['muscle'])
        except Exception:
            current_fat = 25.0
            current_muscle = 30.0
            
        
        log_count = random.randint(10, 20) if user['level'] == 1 else random.randint(20, 40)
        
        for _ in range(log_count):
            activity_id = str(uuid.uuid4())
            log_date = start_date + timedelta(days=random.randint(0, 60))
            
            routine_exercises = random.sample(exercises, k=random.randint(3, 5))
            
            detail_records = []
            ai_item_records = [] 
            routine_score_sum = 0
            total_planned_sets = 0
            
            # -----------------------------------------------------------
            # >>>>>>>>> 수정된 부분 시작: AI 루틴 관련 데이터 생성 및 삽입 (스키마 맞춤) <<<<<<<<<
            ai_routine_id = str(uuid.uuid4())
            
            # 스키마에 맞춘 변수 계산
            goal_type = user['goal']
            if goal_type == 'FAT_LOSS':
                # 목표 체중 감량 (5.0kg ~ 15.0kg)
                target_value = round(random.uniform(5.0, 15.0), 2)
            elif goal_type == 'MUSCLE_GAIN':
                # 목표 근육량 증가 (2.0kg ~ 5.0kg)
                target_value = round(random.uniform(2.0, 5.0), 2)
            else: # MAINTAIN, ENDURANCE
                # 목표 유지/지구력 증가 (임의의 값 1.0)
                target_value = 1.0 
                
            # 예상 시간 (30분 ~ 60분)
            total_time_min = round(random.uniform(30.0, 60.0), 2)
            
            # 예상 칼로리 (레벨에 따라 조정, 250~500 + 레벨 * 100)
            total_calories = round(random.uniform(250.0, 500.0) + user['level'] * 100, 2)
            
            # 1. AI_RECOMMENDED_ROUTINES 생성 (스키마 반영)
            cursor.execute("""
                INSERT INTO ai_recommended_routines (id, user_id, goal_type, target_value, created_at, total_time_min, total_calories)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (ai_routine_id, user['id'], goal_type, target_value, log_date, total_time_min, total_calories))
            # -----------------------------------------------------------

            step_number = 1
            
            for ex in routine_exercises:
                ex_id, ex_name, ex_diff, ex_type, ex_cat = ex
                
                # [핵심 로직] Reps 계산 및 조정
                base_reps = 10 * (user['level'] * 0.4 + 0.6)
                
                # Decimal to Float 오류가 발생하지 않도록 current_fat/muscle 사용
                muscle_bonus = (current_muscle - 30) * 0.4  
                fat_penalty = (current_fat - 20) * 0.3      
                
                goal_bonus = 0
                if ex_cat in ('UPPER_BODY', 'LOWER_BODY', 'FULL_BODY') and user['goal'] == 'MUSCLE_GAIN': goal_bonus += 2
                if ex_type == '유산소' and user['goal'] == 'ENDURANCE': goal_bonus += 2
                diff_penalty = ex_diff * 1.5                
                
                calculated_reps = base_reps + muscle_bonus - fat_penalty + goal_bonus - diff_penalty
                
                reps = int(max(3, min(25, calculated_reps)))
                reps += random.randint(-2, 2)
                
                # AI 루틴에 계획된 세트 수 설정
                planned_sets = random.randint(3, 5) # 3~5 세트 계획
                total_planned_sets += planned_sets
                
                # 2. AI_ROUTINE_ITEMS 레코드 준비
                ai_item_records.append((
                    ai_routine_id, 
                    ex_id, 
                    step_number, 
                    planned_sets, 
                    reps, 
                    random.randint(30, 60) if ex_type == '유산소' else None, # duration_sec 
                    random.randint(30, 60) # rest_sec
                ))
                step_number += 1
                
                # exercise_score (개별 운동의 기준 점수)
                exercise_score = min(100, 60 + (reps * 2) + (user['level'] * 5) + random.randint(-5, 5))
                if user['level'] == 1 and ex_diff >= 4:
                    exercise_score = max(30, exercise_score - 20)
                
                # 실제로 완료된 세트 수 (계획된 세트 수보다 적거나 같게)
                sets_completed = planned_sets - random.randint(0, 1) 
                sets_completed = max(0, sets_completed) # 최소 0 세트
                
                # activity_detail_logs에 넣을 레코드 생성
                for set_num in range(1, sets_completed + 1):
                    set_reps = max(1, reps - (set_num - 1) - random.randint(0, 1))
                    set_score = max(10, exercise_score - (set_num - 1) * 3) # 세트가 진행될수록 점수 미세 하락
                    
                    detail_records.append((activity_id, ex_id, set_num, set_reps, set_score))
                
                routine_score_sum += exercise_score

            # 3. AI_ROUTINE_ITEMS 벌크 삽입
            if ai_item_records:
                ai_item_insert_query = """
                    INSERT INTO ai_routine_items (ai_routine_id, exercise_id, step_number, set_count, reps, duration_sec, rest_sec)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(ai_item_insert_query, ai_item_records)
                total_ai_items += len(ai_item_records)
            # -----------------------------------------------------------


            # Activity Log 저장
            avg_score = routine_score_sum / len(routine_exercises)
            status = 'FINISHED'
            cancellation_reason = None
            
            if user['level'] == 1 and random.random() < 0.3:
                status = 'CANCELED'
                cancellation_reason = random.choice(['TOO_HARD', 'TOO_LONG'])
                avg_score = 0
                
            # completed_ratio 계산 (논리적 연계)
            actual_completed_sets = len(detail_records)
            
            if total_planned_sets == 0:
                completed_ratio = 0.0 
            else:
                calculated_ratio = min(1.0, actual_completed_sets / total_planned_sets)
                completed_ratio = round(calculated_ratio, 2)
            
            # activity_logs 테이블에 ai_routine_id와 completed_ratio 컬럼이 있다고 가정하고 쿼리 실행
            cursor.execute("""
                INSERT INTO activity_logs (id, user_id, ai_routine_id, status, start_time, end_time, cancellation_reason, score, completed_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (activity_id, user['id'], ai_routine_id, status, log_date, log_date + timedelta(minutes=40), cancellation_reason, avg_score, completed_ratio))
            
            total_activity_logs += 1
            
            # Detail Log 저장
            for record in detail_records:
                cursor.execute("""
                    INSERT INTO activity_detail_logs (activity_id, exercise_id, set_number, reps_done, score)
                    VALUES (%s, %s, %s, %s, %s)
                """, record)
                total_detail_logs += 1

    print(f"✅ 총 {total_activity_logs}건의 활동 로그, {total_detail_logs}건의 상세 운동 기록, {total_ai_items}건의 AI 루틴 아이템 생성 완료!")
    
    # ---------------------------------------------------------
    # 6. 최종 검증 (Verification)
    # ---------------------------------------------------------
    print("🔍 데이터 최종 검증 중...")
    cursor.execute(f"SELECT COUNT(*) FROM users WHERE id NOT IN ('{TEST_USER_ID}') AND email NOT IN ('kimchobo@example.com', 'parkjoong@example.com', 'leeadvanced@example.com')")
    dynamic_user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM activity_logs")
    log_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ai_routine_items")
    ai_item_count = cursor.fetchone()[0]
    
    print(f"👍 [검증 완료] 동적 사용자 수: {dynamic_user_count}명")
    print(f"👍 [검증 완료] 전체 활동 로그 수: {log_count}건")
    print(f"👍 [검증 완료] AI 루틴 아이템 수: {ai_item_count}건")


# ---------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------
if __name__ == "__main__":
    conn = None
    try:
        conn = wait_for_db()
        
        # with 구문으로 트랜잭션 시작 (성공 시 자동 Commit, 실패 시 자동 Rollback)
        with conn.cursor() as cursor:
            # 1. 참조 데이터 삽입 (Exercise, Config 등)
            insert_reference_data(cursor)
            
            # 2. 기존 더미 데이터 정리
            clean_dynamic_data(cursor)
            
            # 3. 기초 데이터 로드 및 검증
            exercises = get_exercises(cursor)
            if not exercises:
                raise Exception("❌ 필수 데이터 오류: exercise 테이블이 비어 있거나 참조 데이터 삽입에 실패했습니다. SQL 스키마를 확인하십시오.")
                
            # 4. 동적 데이터 생성
            # 고정 사용자 포함 총 104명의 사용자 객체 생성 (동적 100명 + 고정 4명)
            users = create_users_with_flexible_logic(cursor, count=100)
            
            # 5. 로그 생성
            create_logical_activity_logs(cursor, users, exercises)
            
            conn.commit()
            print("🎉🎉🎉 모든 데이터 생성이 성공적으로 완료되었으며 DB에 커밋되었습니다! 🎉🎉🎉")
            
    except Exception as e:
        print(f"❌ 데이터 생성 중 치명적 오류 발생 (롤백됨): {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


