# 🗺️ Feature-Backend Mapping

프론트엔드 기능별 백엔드 구조 상세 매핑 문서입니다.

---

## 📥 Part 1: 데이터 출처별 백엔드 처리

### 1. ZIP 파일 업로드 (웹)

**프론트엔드**: `UploadPage.jsx`

**API 엔드포인트**: `POST /api/file/upload`

**백엔드 처리 흐름**:

```
file_upload_api.py
│
└─ upload_file(file, user_id, difficulty, duration)
    │
    └─ file_upload_service.py → process_file()
        │
        ├─ 1. 파일 저장 (임시 디렉토리)
        │      └─ tempfile.mkdtemp()
        │
        ├─ 2. ZIP/DB 판별 및 압축 해제
        │      └─ unzipper.py → extract_zip_to_temp()
        │          └─ is_sqlite_file() 시그니처 검사
        │
        ├─ 3. SQLite → JSON 변환
        │      └─ db_to_json.py → db_to_json()
        │          └─ 모든 테이블 → dict 변환
        │
        ├─ 4. 플랫폼 감지
        │      └─ detect_platform(filename, db_json)
        │          ├─ 파일명 기반: "healthconnect" → samsung
        │          └─ DB 구조 기반: steps_record_table 존재 → samsung
        │
        ├─ 5. 날짜별 데이터 추출
        │      └─ db_parser.py → parse_db_json_to_raw_data_by_day()
        │          ├─ Epoch Day (19992) → 날짜 그룹핑
        │          ├─ 각 테이블 데이터 집계 (_mean, _total)
        │          └─ 날짜별 raw_json 생성
        │
        ├─ 6. 전처리 (모든 날짜)
        │      └─ preprocess.py → preprocess_health_json()
        │          ├─ normalize_raw() - 23개 필드 정규화
        │          ├─ None 값 → 0 안전 변환
        │          ├─ 단위 통합 (cm→m, g→kg 등)
        │          └─ epoch_day_to_date_string() 날짜 변환
        │
        ├─ 7. VectorDB 배치 저장
        │      └─ vector_store.py → save_daily_summaries_batch()
        │          ├─ preprocess_for_embedding.py → summary_to_natural_text()
        │          ├─ 배치 임베딩 생성 (OpenAI API)
        │          ├─ doc_id: "{user_id}_{date}_{source}"
        │          └─ upsert로 중복 방지
        │
        └─ 8. LLM 분석 (최신 날짜만)
               └─ llm_analysis.py → run_llm_analysis()
```

**주요 코드**:

```python
# file_upload_service.py
source = f"zip_{platform}"  # "zip_samsung" or "zip_apple"
await self.run_blocking(
    save_daily_summaries_batch, all_summaries, user_id, source
)
```

---

### 2. 삼성 앱 API 업로드

**앱**: React Native (`useHealthConnect.ts` + `index.tsx`)

**API 엔드포인트**: `POST /api/auto/upload`

**백엔드 처리 흐름**:

```
auto_upload_api.py
│
└─ upload_json(payload: UploadRequest)
    │
    ├─ Request Body:
    │      ├─ user_id: str
    │      ├─ date: str (YYYY-MM-DD)
    │      ├─ raw_json: dict (23개 필드)
    │      ├─ difficulty: str
    │      └─ duration: int
    │
    └─ auto_upload_service.py → process_json()
        │
        ├─ 1. 플랫폼 자동 감지
        │      └─ platform = "samsung" (삼성 Health Connect)
        │      └─ platform = "apple" (애플 HealthKit)
        │      ※ 현재는 auto_upload_api.py에서 구분되어 전달됨
        │
        ├─ 2. Summary 생성
        │      └─ preprocess.py → preprocess_health_json()
        │          ├─ date_int 변환: "2025-12-17" → 20251217
        │          └─ platform 정보 활용
        │
        ├─ 3. VectorDB 저장
        │      └─ vector_store.py → save_daily_summary()
        │          ├─ source = f"api_{platform}"  # "api_samsung" or "api_apple"
        │          └─ doc_id: "{user_id}_{date}_api_{platform}"
```

**앱 전송 데이터 형식**:

```typescript
// useHealthConnect.ts
const payload = {
  user_id: email,
  date: '2025-12-17', // YYYY-MM-DD
  raw_json: {
    sleep_min: 450,
    sleep_hr: 7.5,
    weight: 70,
    height_m: 1.75,
    steps: 8000,
    distance_km: 5.2,
    heart_rate: 72,
    resting_heart_rate: 62,
    // ... 23개 필드
  },
  difficulty: '중',
  duration: 30,
};
```

---

### 3. 애플 앱 API 업로드

**앱**: Swift (`HealthUploader.swift` + `HealthUploadModel.swift`)

**API 엔드포인트**: `POST /api/auto/upload` (삼성과 동일)

**백엔드 처리 흐름**: 삼성과 동일하나, platform = "apple"로 설정

※ 차이점:

- platform: "apple"
- source: "api_apple"
- doc_id: "user@email.com_2025-12-17_api_apple"

**앱 전송 데이터 형식**:

```swift
// HealthUploadModel.swift
struct HealthUploadModel: Codable {
    let user_id: String
    let date: String          // ✅ YYYY-MM-DD (필수!)
    let difficulty: String
    let duration: Int
    let raw_json: HealthData
}

// 단위 변환 (Swift → 백엔드)
raw_json = HealthData(
    sleep_min: sleepHours / 60.0,      // 초 → 분
    sleep_hr: sleepHours / 3600.0,     // 초 → 시간
    distance_km: distance / 1000.0,    // 미터 → km
    oxygen_saturation: oxygen,          // % 그대로
    // ...
)
```

**주요 수정사항 (422 에러 해결)**:

- `date` 필드 추가 (백엔드 필수 필드)
- 필드명 백엔드 매칭 (`sleep_hr`, `oxygen_saturation` 등)
- 단위 변환 (초→분, 미터→킬로미터)

---

### 플랫폼별 데이터 소스 비교

| 구분            | Samsung (ZIP)                  | Samsung (API)                 | Apple (API)                 |
| --------------- | ------------------------------ | ----------------------------- | --------------------------- |
| **데이터 형태** | SQLite DB                      | JSON                          | JSON                        |
| **날짜 형식**   | Epoch Day (19992) → YYYY-MM-DD | YYYY-MM-DD                    | YYYY-MM-DD                  |
| **처리 경로**   | db_parser → preprocess         | preprocess 직접               | preprocess 직접             |
| **플랫폼 감지** | detect_platform() 함수         | 자동 설정 ("samsung")         | 자동 설정 ("apple")         |
| **source 값**   | `zip_samsung`                  | `api_samsung`                 | `api_apple`                 |
| **doc_id 예시** | `user_2025-12-17_zip_samsung`  | `user_2025-12-17_api_samsung` | `user_2025-12-17_api_apple` |

---

## 📊 Part 2: 생체 데이터 분석 서비스

**프론트엔드**: `AnalysisPage.jsx`

**API 엔드포인트**: `GET /api/user/latest-analysis`

### 백엔드 처리 흐름

```
user_api.py → get_latest_analysis()
│
├─ Query Parameters:
│      ├─ user_id: str (필수)
│      ├─ difficulty: str (기본 "중")
│      └─ duration: int (기본 30)
│
├─ 1. VectorDB에서 최신 데이터 조회
│      └─ collection.get(where={"user_id": user_id})
│          │
│          ├─ 날짜 기준 정렬 (최신순)
│          │      sorted(metadatas, key=lambda x: x["date"], reverse=True)
│          │
│          ├─ summary_json 파싱 → raw 데이터 추출
│          │      summary_dict = json.loads(summary_json)
│          │      raw_data = summary_dict["raw"]
│          │
│          └─ 데이터 품질 검증
│                 ├─ 수면 데이터 존재 여부
│                 ├─ 활동량 데이터 존재 여부
│                 └─ 출처 분석 (API vs ZIP)
│
├─ 2. Summary 형식 재구성
│      summary = {
│          "created_at": date,
│          "summary_text": summary_text,
│          "raw": raw_data
│      }
│
└─ 3. AI 분석
       └─ llm_analysis.py → run_llm_analysis()
           │
           ├─ [규칙 기반 해석]
           │   └─ health_interpreter.py
           │       ├─ interpret_health_data(raw)
           │       │      ├─ interpret_sleep()
           │       │      ├─ interpret_heart_rate()
           │       │      ├─ interpret_activity()
           │       │      ├─ interpret_bmi()
           │       │      └─ interpret_oxygen()
           │       │
           │       ├─ calculate_health_score(raw)
           │       │      └─ 수면/활동/심박/BMI 가중 평균 → 0~100점
           │       │
           │       └─ recommend_exercise_intensity(raw)
           │              └─ 건강점수 + 수면 + 활동량 기반 → 하/중/상
           │
           ├─ [RAG 검색]
           │   └─ vector_store.py → search_similar_summaries()
           │       ├─ build_rag_query(raw) → 쿼리 생성
           │       ├─ 벡터 유사도 검색 (top_k=3)
           │       └─ classify_rag_strength() → none/weak/strong
           │
           ├─ [Fallback 판단]
           │   ├─ 강도 "하" → Fallback ✅
           │   ├─ 점수 < 50 → Fallback ✅
           │   └─ 데이터 부족 → Fallback ✅
           │
           └─ [LLM 호출 또는 Fallback]
               ├─ Fallback: get_fallback_routine()
               │      └─ 난이도별 운동 풀에서 선택
               │
               └─ LLM: OpenAI API 호출
                      ├─ System Prompt (RAG 상태별 가이드)
                      ├─ User Prompt (건강 데이터 + 운동 목록)
                      └─ validate_routine() 검증
```

### 응답 구조

```json
{
  "success": true,
  "user_id": "user@email.com",
  "date": "2025-12-17",
  "summary": {
    "summary_text": "수면 7.5시간 / 걸음수 8,000보 / 심박수 72bpm",
    "raw": {
      "sleep_min": 450,
      "sleep_hr": 7.5,
      "steps": 8000,
      "heart_rate": 72
      // ... 23개 필드
    }
  },
  "analysis": "오늘 컨디션 분석 결과...",
  "ai_recommended_routine": {
    "total_time_min": 30,
    "total_calories": 180,
    "items": [
      {
        "exercise_name": "crunch",
        "category": [2],
        "difficulty": 4,
        "met": 4.5,
        "duration_sec": 30,
        "rest_sec": 15,
        "set_count": 3,
        "reps": null
      }
    ]
  },
  "detailed_health_report": "종합 건강 분석 리포트..."
}
```

---

## 🏃 Part 3: 운동 추천 서비스

**프론트엔드**: `AnalysisPage.jsx` (난이도/시간 선택 포함)

**API 엔드포인트**: `GET /api/user/latest-analysis`

### 운동 강도/기간 선택 옵션

| 파라미터     | 옵션                 | 기본값 |
| ------------ | -------------------- | ------ |
| `difficulty` | 하, 중, 상           | 중     |
| `duration`   | 10, 20, 30, 40, 60분 | 30     |

### 강도별 MET 범위

| 강도 | MET 범위  | 운동 예시                                 |
| ---- | --------- | ----------------------------------------- |
| 하   | 2.5 - 4.0 | standing knee up, hip thrust, cross lunge |
| 중   | 4.0 - 5.0 | crunch, lying leg raise, knee push up     |
| 상   | 5.0 - 8.0 | burpee, plank, push up, bicycle crunch    |

### Fallback 루틴 생성 로직

```
get_fallback_routine(difficulty_level, duration_min, raw)
│
├─ 1. 난이도별 운동 풀 선택
│      exercise_pools = {
│          "하": [...],
│          "중": [...],
│          "상": [...]
│      }
│
├─ 2. 시간대별 설정
│      ├─ 10~15분: 2-3세트, 휴식 10-15초
│      ├─ 20~30분: 3-4세트, 휴식 15초
│      └─ 40~60분: 4-5세트, 휴식 20초
│
├─ 3. 운동 순환 선택
│      └─ 목표 시간 도달까지 운동 풀에서 순차 선택
│
├─ 4. 분석 텍스트 생성
│      └─ build_analysis_text() 호출
│
└─ 5. 결과 반환
       {
           "analysis": "...",
           "ai_recommended_routine": {...},
           "detailed_health_report": "..."
       }
```

---

## 🤖 Part 4: 챗봇 서비스

### 4-1. 자유형 챗봇

**프론트엔드**: `ChatPage.jsx` - 텍스트 입력

**API 엔드포인트**: `POST /api/chat`

**백엔드 처리 흐름**:

```
chat_api.py → chat()
│
├─ Request Body:
│      {
│          "user_id": "user@email.com",
│          "message": "오늘 컨디션 어때?",
│          "character": "devil_coach"
│      }
│
└─ chat_service.py → handle_chat()
    │
    └─ chat_generator.py → generate()
        │
        ├─ 1. 의도 분류
        │      └─ intent_classifier.py → classify_intent()
        │          │
        │          ├─ 규칙 기반 분류 (GPT 호출 없음!)
        │          │      ├─ HEALTH_KEYWORDS 매칭 → "health_query"
        │          │      ├─ ROUTINE_KEYWORDS 매칭 → "routine_request"
        │          │      └─ 매칭 없음 → "default_chat"
        │          │
        │          └─ 캐시 적용 (5분 TTL)
        │
        ├─ 2. 캐릭터 페르소나 로드
        │      └─ persona.py → get_persona_prompt()
        │          ├─ "devil_coach": 악마 코치 (지옥 훈련!)
        │          ├─ "angel_coach": 천사 코치 (따뜻한 격려)
        │          └─ "booster_coach": 부스터 코치 (하이텐션!)
        │
        ├─ 3. [health_query] 건강 데이터 질문
        │      ├─ RAG 검색
        │      │      └─ rag_query.py → query_health_data()
        │      │          └─ search_similar_summaries()
        │      │
        │      ├─ 건강 컨텍스트 생성
        │      │      └─ build_health_context_for_llm()
        │      │
        │      └─ OpenAI API 호출 (max_tokens=300)
        │
        ├─ 4. [routine_request] 운동 루틴 요청
        │      ├─ RAG 검색
        │      ├─ 건강 해석
        │      │      └─ interpret_health_data()
        │      │
        │      ├─ LLM 분석
        │      │      └─ run_llm_analysis()
        │      │
        │      └─ 템플릿 응답 생성
        │             └─ _format_routine_response()
        │
        └─ 5. [default_chat] 일반 대화
               └─ OpenAI API 호출 (max_tokens=150)
```

### 의도 분류 키워드

```python
# intent_classifier.py

HEALTH_KEYWORDS = [
    # 수면
    "수면", "잠", "sleep", "몇시간", "잤",
    # 신체
    "체중", "몸무게", "키", "bmi", "체지방",
    # 활동
    "걸음", "steps", "이동거리", "운동시간",
    # 칼로리
    "칼로리", "열량", "소모",
    # 바이탈
    "심박", "맥박", "산소포화", "혈압", "혈당",
    # 상태 질문
    "내 상태", "컨디션", "건강 어때", "오늘 어때"
]

ROUTINE_KEYWORDS = [
    "운동 추천", "루틴", "홈트", "하체", "상체", "전신",
    "운동 알려줘", "30분 운동", "유산소", "코어"
]
```

---

### 4-2. 고정형 챗봇

**프론트엔드**: `ChatPage.jsx` - 버튼 클릭

**API 엔드포인트**: `POST /api/chat/fixed`

**질문 타입별 매핑**:

| 버튼                   | question_type          | 백엔드 함수                        |
| ---------------------- | ---------------------- | ---------------------------------- |
| 📊 이번 주 건강 리포트 | `weekly_report`        | `_generate_weekly_report()`        |
| 🔥 오늘 운동 추천      | `today_recommendation` | `_generate_today_recommendation()` |
| 🚶 지난주 걸음수       | `weekly_steps`         | `_generate_steps_report()`         |
| 😴 수면 분석           | `sleep_report`         | `_generate_sleep_report()`         |
| ❤️ 심박수 분석         | `heart_rate`           | `_generate_heart_rate_report()`    |
| 🏅 건강 점수           | `health_score`         | `_generate_health_score_report()`  |

**백엔드 처리 흐름**:

```
chat_api.py → chat_fixed()
│
├─ Request Body:
│      {
│          "user_id": "user@email.com",
│          "question_type": "today_recommendation",
│          "character": "devil_coach"
│      }
│
└─ chat_service.py → handle_fixed_chat()
    │
    └─ fixed_responses.py → generate_fixed_response()
        │
        ├─ 1. VectorDB 검색 (최근 5일)
        │      └─ search_similar_summaries(top_k=5)
        │
        ├─ 2. 규칙 기반 건강 해석
        │      └─ interpret_health_data(recent_raw)
        │
        └─ 3. 질문 타입별 처리
            │
            ├─ [weekly_report]
            │      ├─ 7일 데이터 집계 (걸음, 칼로리, 수면)
            │      └─ LLM 호출 (주간 리포트 생성)
            │
            ├─ [today_recommendation] ⭐
            │      ├─ run_llm_analysis() 호출
            │      └─ 캐릭터별 템플릿 응답
            │          templates = {
            │              "devil_coach": {
            │                  "intro": "인간, 오늘 지옥 훈련 메뉴다!",
            │                  "outro": "이 정도는 워밍업이다!"
            │              },
            │              ...
            │          }
            │
            ├─ [weekly_steps]
            │      ├─ 7일 걸음수 집계
            │      └─ LLM 호출 (걸음수 분석)
            │
            ├─ [sleep_report]
            │      ├─ 7일 수면 데이터 집계
            │      └─ LLM 호출 (수면 분석)
            │
            ├─ [heart_rate]
            │      └─ LLM 호출 (심박수 분석)
            │
            └─ [health_score]
                   ├─ calculate_health_score()
                   └─ LLM 호출 (점수 해석)
```

### 캐릭터 페르소나 상세

```python
# persona.py

personas = {
    "devil_coach": """
    너는 '헬스 지옥의 PT장'이라는 별명을 가진 악마 코치다.
    말투 특징:
    - 유저를 '인간' 이라고 부른다
    - 위압적이지만, 중간중간 농담처럼 웃긴 표현을 섞는다
    예시: "인간, 오늘도 핑계의 연기로 가득하군. 지옥의 난이도로 조져주지."
    """,

    "angel_coach": """
    너는 '하늘계 헬스 수호천사'라는 별명을 가진 천사 코치다.
    말투 특징:
    - "당신", "괜찮아요", "함께 해봐요" 같은 따뜻한 단어 사용
    - 꾸짖는 말 절대 없음
    예시: "당신의 몸과 마음이 빛나고 있어요."
    """,

    "booster_coach": """
    너는 '부스터맨'이라는 별명을 가진 텐션 끝판왕 코치다.
    말투 특징:
    - "가자!", "부스트!", "파워업!" 등 폭발적 리액션
    - 사용자의 작은 변화도 크게 칭찬
    예시: "렛츠고오오오!!! 심박수 슈우웅↑ 올라간다아아!!"
    """
}
```

---

## 📋 23개 정규화 필드

```python
# preprocess.py → normalize_raw()
{
    # 수면
    "sleep_min": 0,        # 분
    "sleep_hr": 0,         # 시간

    # 신체 계측
    "weight": 0,           # kg
    "height_m": 0,         # m
    "bmi": 0,
    "body_fat": 0,         # %
    "lean_body": 0,        # kg

    # 활동
    "distance_km": 0,      # km
    "steps": 0,
    "steps_cadence": 0,
    "exercise_min": 0,     # 분
    "flights": 0,          # 층

    # 칼로리
    "active_calories": 0,  # kcal
    "total_calories": 0,   # kcal
    "calories_intake": 0,  # kcal

    # 심박/바이탈
    "oxygen_saturation": 0, # %
    "heart_rate": 0,        # bpm
    "resting_heart_rate": 0,
    "walking_heart_rate": 0,
    "hrv": 0,               # ms
    "systolic": 0,          # mmHg
    "diastolic": 0,         # mmHg
    "glucose": 0,           # mg/dL
}
```
