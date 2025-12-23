# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ZIP 파일 데이터 확인 (백엔드에서 확인!!)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

python inspect_data.py --zip-list # ZIP 파일 목록

# python inspect_data.py --zip-latest # (아래 샘플 참고) 최신 ZIP 테이블 요약

# python inspect_data.py --zip-latest --parsed # (아래 샘플 참고) 최신 ZIP 정제 데이터

python inspect_data.py --zip-latest --table <테이블> # 최신 ZIP 특정 테이블
python inspect_data.py --zip <경로> # 특정 ZIP 테이블 요약
python inspect_data.py --zip <경로> --table <테이블> # 특정 ZIP 특정 테이블
python inspect_data.py --zip <경로> --parsed # 특정 ZIP 정제 데이터

# 샘플(25.12.19 추출하고, 25.12.18 확인된 실제 데이터)

# python inspect_data.py --zip-latest(최신 ZIP 테이블 요약)

📋 총 테이블 수: 72개

테이블명 레코드 컬럼 수

✅ heart_rate_record_series_table 685258 3
✅ speed_record_table 23192 3
✅ heart_rate_record_table 4021 16
✅ sleep_stages_table 3232 4
✅ activity_date_table 1511 3
✅ read_access_logs_table 1249 6
✅ steps_record_table 407 17
✅ total_calories_burned_record_table 349 17
✅ exercise_session_record_table 349 22
✅ distance_record_table 278 17
✅ SpeedRecordTable 276 16
✅ change_log_request_table 236 7
✅ sleep_session_record_table 48 18
✅ oxygen_saturation_record_table 47 14
✅ preference_table 18 2
✅ sqlite_sequence 15 2
✅ height_record_table 14 14
✅ weight_record_table 14 14
✅ application_info_table 7 5
✅ health_data_category_priority_table 5 3
✅ device_info_table 2 4
✅ android_metadata 1 1
⚠️ active_calories_burned_record_table 0 0
--- 이하 생략 ---

# python inspect_data.py --zip-latest --parsed(최신 ZIP 정제 데이터)

📅 총 410일치 데이터 추출됨

📊 데이터가 있는 필드 (총 9개):
steps : 407일
heartRate : 361일
totalCaloriesBurned : 167일
distance : 158일
sleep : 36일
sleep_hr : 36일
oxygenSaturation : 34일
weight : 12일
height : 12일

📅 날짜별 데이터 (최근 10일):

──────────────────────────────────────────────────
📅 2025-12-18
sleep: 362.0
sleep_hr: 6.033333333333333 시간
steps: 3,706
heartRate: 79.79773462783172
oxygenSaturation: 92.0

──────────────────────────────────────────────────
📅 2025-12-17
sleep: 289.0
sleep_hr: 4.816666666666666 시간
weight: 54.5
height: 1.63
steps: 3,650
heartRate: 84.48864994026285
oxygenSaturation: 96.33333333333333

──────────────────────────────────────────────────
--- 이하 생략 ---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# VectorDB 데이터 확인 (백엔드에서 확인!!)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

python inspect_data.py --all # 전체 데이터 요약
python inspect_data.py --user <이메일> # 특정 사용자 데이터
python inspect_data.py --user <이메일> --detail # 상세 정보
python inspect_data.py --user <이메일> --detail --all-fields # 모든 필드
python inspect_data.py --date <YYYY-MM-DD> --user <이메일> # 특정 날짜
python inspect_data.py --duplicates # 중복 데이터 확인
python inspect_data.py --dates # 날짜 범위 확인
python inspect_data.py --location # ChromaDB 위치

python inspect_data.py --delete-old # 예전 형식 데이터 삭제, 미리보기 (삭제 안 함)
python inspect_data.py --delete-old --confirm # 예전 형식 데이터 삭제, 실제 삭제
python inspect_data.py --delete-source api --confirm # 특정 출처(source) 삭제, source가 'api'인 것만 삭제 (예전 형식)
python inspect_data.py --delete-source zip --confirm # 특정 출처(source) 삭제, ource가 'zip'인 것만 삭제
python inspect_data.py --delete-user test123@aaa.com # 특정 사용자 전체 삭제, 미리보기
python inspect_data.py --delete-user test123@aaa.com --confirm # 특정 사용자 전체 삭제, 실제 삭제

###### 샘플(25.12.19. 15:29 실시간 데이터)

# python inspect_data.py --all
