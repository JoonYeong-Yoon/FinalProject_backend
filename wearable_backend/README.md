# 🏋️ Wearable Health Data AI Trainer - Backend

웨어러블 헬스 데이터 기반 AI 트레이너 서비스의 백엔드 시스템입니다.

---

## 📁 폴더 구조

```
backend/
├── main.py                 # FastAPI 앱 진입점
├── config.py               # 환경설정 (LLM, API, ChromaDB)
├── requirements.txt        # 의존성 패키지
├── .env                    # 환경변수 (API 키 등)
├── chroma_data/            # ChromaDB 영구 저장소
│
├── app/
│   ├── api/                        # API 라우터 레이어
│   │   ├── auto_upload_api.py      # 앱 자동 업로드 API
│   │   ├── chat_api.py             # 챗봇 API
│   │   ├── file_upload_api.py      # ZIP 파일 업로드 API
│   │   ├── similar_api.py          # 유사도 검색 API
│   │   └── user_api.py             # 사용자 분석 API
│   │
│   ├── core/                       # 핵심 비즈니스 로직
│   │   ├── health_interpreter.py   # 규칙 기반 건강 해석기
│   │   ├── llm_analysis.py         # LLM 분석 엔진
│   │   ├── rag_query.py            # RAG 쿼리 빌더
│   │   ├── vector_store.py         # ChromaDB 벡터 저장소
│   │   ├── db_parser.py            # Samsung DB 파서
│   │   ├── db_to_json.py           # SQLite → JSON 변환
│   │   ├── unzipper.py             # ZIP 압축해제
│   │   ├── adaptive_threshold.py   # 적응형 임계값 계산
│   │   │
│   │   └── chatbot_engine/         # 챗봇 엔진
│   │       ├── chat_generator.py   # 자유형 챗봇 응답 생성
│   │       ├── fixed_responses.py  # 고정형 질문 응답
│   │       ├── intent_classifier.py # 의도 분류기
│   │       ├── persona.py          # 캐릭터 페르소나
│   │       └── rag_query.py        # 챗봇용 RAG 쿼리
│   │
│   ├── service/                    # 서비스 레이어
│   │   ├── auto_upload_service.py  # 자동 업로드 처리
│   │   ├── file_upload_service.py  # 파일 업로드 처리
│   │   ├── chat_service.py         # 챗봇 서비스
│   │   └── similar_service.py      # 유사도 검색 서비스
│   │
│   └── utils/                      # 유틸리티
│       ├── preprocess.py           # 건강 데이터 전처리
│       ├── preprocess_for_embedding.py # 임베딩용 텍스트 생성
│       └── platform_detection.py   # 플랫폼 자동 감지
```

---

## 🔄 운동추천 서비스: Fallback + LLM 워크플로우

### 전체 흐름 트리

```
run_llm_analysis(summary, user_id, difficulty_level, duration_min)
│
├─ 1. RAG 검색 (과거 유사 패턴 조회)
│      └─ search_similar_summaries(query_dict, user_id, top_k=3)
│          └─ 벡터 유사도 기반 과거 데이터 검색
│
├─ 2. 규칙 기반 건강 해석 (LLM 호출 없음)
│      ├─ build_health_context_for_llm(raw)
│      ├─ recommend_exercise_intensity(raw)
│      │      └─ recommended_level 결정 → "하" / "중" / "상" ⭐
│      └─ calculate_health_score(raw)
│             └─ score 계산 → 0~100점 ⭐
│
├─ 3. Fallback 조건 판단 (recommended_level과 score 활용)
│      ├─ [조건 1] recommended_level == "하" → Fallback ✅
│      ├─ [조건 2] score < 50 → Fallback ✅
│      ├─ [조건 3] !check_data_quality(raw) → Fallback ✅
│      │
│      ├─ [조건 충족] → get_fallback_routine() 호출 → 즉시 반환
│      └─ [조건 미충족] → LLM 호출 진행
│
├─ 4. LLM 호출 (OpenAI API)
│      ├─ System Prompt 구성 (RAG 상태별 가이드)
│      ├─ User Prompt 구성 (건강 데이터 + 운동 목록)
│      └─ client.chat.completions.create()
│
├─ 5. LLM 결과 검증
│      ├─ JSON 파싱 검증
│      ├─ validate_routine() 호출
│      │      ├─ 시간 검증: 목표 시간 ±20% 이내
│      │      └─ MET 범위 검증: 난이도별 허용 범위
│      │
│      ├─ [검증 성공] → LLM 결과 반환
│      └─ [검증 실패] → Fallback 반환
│
└─ 6. 예외 처리
       └─ LLM 호출/파싱 실패 → Fallback 반환
```

### Fallback 조건 상세

| 조건           | 코드                        | 설명                 | 이유                                         |
| -------------- | --------------------------- | -------------------- | -------------------------------------------- |
| 권장 강도 "하" | `recommended_level == "하"` | 시스템이 저강도 권장 | 안전 모드 - LLM 없이 검증된 저강도 루틴 제공 |
| 건강 점수 낮음 | `score < 50`                | 50점 미만            | 건강 상태 불량 - 안전한 규칙 기반 루틴 필요  |
| 데이터 부족    | `!check_data_quality(raw)`  | 수면/활동량 모두 0   | 분석 근거 부족 - LLM 판단 불가               |

### LLM 호출하는 경우

- 권장 강도가 "중" 또는 "상"
- 건강 점수 50점 이상
- 수면 또는 활동량 데이터 존재
- RAG 결과 활용 가능 (과거 패턴 참고)

---

## 📊 파일별 주요 함수 목록

### `health_interpreter.py` - 규칙 기반 건강 해석기

| 함수                                 | 용도                                |
| ------------------------------------ | ----------------------------------- |
| `interpret_sleep(raw)`               | 수면 시간 → 상태/레벨/권장사항 해석 |
| `interpret_heart_rate(raw)`          | 심박수 → 피트니스 레벨 판정         |
| `interpret_activity(raw)`            | 걸음수 → 활동 레벨 분류             |
| `interpret_bmi(raw)`                 | BMI → 체형 카테고리 + 운동 추천     |
| `interpret_oxygen(raw)`              | 산소포화도 해석                     |
| `calculate_health_score(raw)`        | 종합 건강 점수 (0~100) 계산 ⭐      |
| `recommend_exercise_intensity(raw)`  | 권장 운동 강도 (하/중/상) 결정 ⭐   |
| `interpret_health_data(raw)`         | 위 함수들 종합 호출                 |
| `build_health_context_for_llm(raw)`  | LLM 프롬프트용 컨텍스트 생성        |
| `build_analysis_text(...)`           | Fallback용 상세 분석 텍스트 ✨      |
| `analyze_rag_patterns(similar_days)` | RAG 유사 패턴 분석                  |

### `llm_analysis.py` - LLM 분석 엔진

| 함수                                                       | 용도                     |
| ---------------------------------------------------------- | ------------------------ |
| `run_llm_analysis(summary, user_id, difficulty, duration)` | 메인 분석 함수 ⭐        |
| `check_data_quality(raw)`                                  | 최소 데이터 품질 확인    |
| `validate_routine(result, difficulty, target_min)`         | LLM 결과 검증 (시간/MET) |
| `get_fallback_routine(difficulty, duration, raw)`          | Fallback 루틴 생성 ✨    |
| `build_detailed_health_analysis(raw)`                      | 상세 건강 리포트 생성    |
| `clean_json_text(text)`                                    | JSON 마크다운 정리       |
| `try_parse_json(text)`                                     | 안전한 JSON 파싱         |

### `vector_store.py` - VectorDB 관리

| 함수                                                     | 용도                          |
| -------------------------------------------------------- | ----------------------------- |
| `save_daily_summary(summary, user_id, source)`           | 단일 summary 저장 (upsert) ⭐ |
| `save_daily_summaries_batch(summaries, user_id, source)` | 배치 저장                     |
| `search_similar_summaries(query_dict, user_id, top_k)`   | 유사 패턴 검색 ⭐             |
| `embed_text(text)`                                       | 단일 텍스트 임베딩 생성       |
| `batch_embed_texts(texts)`                               | 배치 임베딩 생성              |
| `get_cached_embedding(text)`                             | 캐시된 임베딩 반환            |

### `preprocess.py` - 데이터 전처리

| 함수                                                   | 용도                              |
| ------------------------------------------------------ | --------------------------------- |
| `preprocess_health_json(raw_json, date_int, platform)` | 메인 전처리 함수 ⭐               |
| `normalize_raw(raw_json)`                              | 23개 필드 정규화 (None 안전 처리) |
| `generate_summary_text(raw)`                           | 요약 텍스트 생성                  |
| `epoch_day_to_date_string(epoch_day)`                  | Epoch Day → YYYY-MM-DD 변환       |

### `file_upload_service.py` - ZIP 파일 처리

| 함수                                                | 용도                    |
| --------------------------------------------------- | ----------------------- |
| `process_file(file, user_id, difficulty, duration)` | 메인 처리 함수 ⭐       |
| `detect_platform(filename, db_json)`                | Apple/Samsung 자동 감지 |
| `run_blocking(func, *args)`                         | 동기 함수 비동기 실행   |
| `get_or_create_user_id(user_id)`                    | user_id 생성/검증       |

### `auto_upload_service.py` - 앱 API 처리

| 함수                                                           | 용도                |
| -------------------------------------------------------------- | ------------------- |
| `process_json(json_data, user_id, date, difficulty, duration)` | JSON 데이터 처리 ⭐ |
| `get_or_create_user_id(user_id)`                               | user_id 생성/검증   |

### `chat_generator.py` - 자유형 챗봇

| 함수                                                             | 용도                   |
| ---------------------------------------------------------------- | ---------------------- |
| `generate(user_id, message, character)`                          | 메인 응답 생성 함수 ⭐ |
| `_call_openai(system_prompt, user_prompt, max_tokens)`           | OpenAI API 호출        |
| `_build_system_prompt(persona_prompt, context_type)`             | 시스템 프롬프트 구성   |
| `_format_rag_brief(rag)`                                         | RAG 결과 간소화        |
| `_format_routine_response(character, analysis, routine, health)` | 루틴 응답 포맷팅       |

### `fixed_responses.py` - 고정형 챗봇

| 함수                                                         | 용도                |
| ------------------------------------------------------------ | ------------------- |
| `generate_fixed_response(user_id, question_type, character)` | 메인 응답 생성 ⭐   |
| `_get_no_data_response(character)`                           | 데이터 없을 때 응답 |
| `_generate_weekly_report(...)`                               | 주간 건강 리포트    |
| `_generate_today_recommendation(...)`                        | 오늘 운동 추천 ⭐   |
| `_generate_steps_report(...)`                                | 걸음수 분석         |
| `_generate_sleep_report(...)`                                | 수면 분석           |
| `_generate_heart_rate_report(...)`                           | 심박수 분석         |
| `_generate_health_score_report(...)`                         | 건강 점수 리포트    |

### `intent_classifier.py` - 의도 분류기

| 함수                          | 용도                      |
| ----------------------------- | ------------------------- |
| `classify_intent(message)`    | 메인 의도 분류 함수 ⭐    |
| `_rule_based_intent(message)` | 규칙 기반 분류 (GPT 없음) |
| `_cache_get(key)`             | 캐시 조회                 |
| `_cache_set(key, intent)`     | 캐시 저장                 |

### `db_parser.py` - Samsung DB 파서

| 함수                                        | 용도                       |
| ------------------------------------------- | -------------------------- |
| `parse_db_json_to_raw_data_by_day(db_json)` | 날짜별 raw 데이터 생성 ⭐  |
| `parse_db_json_to_raw_data(db_json)`        | 최신 1일치만 반환 (호환용) |
| `_init_day_bucket()`                        | 날짜별 데이터 버킷 초기화  |

### `rag_query.py` (core) - RAG 쿼리 빌더

| 함수                                  | 용도                          |
| ------------------------------------- | ----------------------------- |
| `build_rag_query(raw)`                | RAG 검색용 query dict 생성 ⭐ |
| `classify_rag_strength(similar_days)` | RAG 결과 신뢰 수준 분류       |

---

## 🗄️ VectorDB 데이터 확인 방법

### 1. API 엔드포인트 사용

```bash
# 전체 VectorDB 상태 확인
curl http://localhost:8000/api/vectordb/status

# 특정 사용자 데이터 조회
curl http://localhost:8000/api/vectordb/user/{user_id}

# 사용자 raw history 조회
curl "http://localhost:8000/api/user/raw-history?user_id={user_id}"
```

### 2. Python 스크립트 사용

```python
# check_vectordb.py
from app.core.vector_store import collection, search_similar_summaries

# 전체 데이터 개수
print(f"총 데이터: {collection.count()}개")

# 특정 사용자 데이터 조회
result = collection.get(where={"user_id": "user@email.com"})

# 날짜별 정렬
dates = sorted([m["date"] for m in result["metadatas"]], reverse=True)
print(f"최신 날짜: {dates[0]}")

for meta in result["metadatas"][:5]:
    print(f"날짜: {meta['date']}, 출처: {meta['source']}, 점수: {meta['health_score']}")

# 유사 패턴 검색
similar = search_similar_summaries(
    query_dict={"query": "health summary"},
    user_id="user@email.com",
    top_k=5
)
for day in similar["similar_days"]:
    print(f"{day['date']}: {day['summary_text'][:50]}...")
```

### 3. main.py 내장 API

```python
# GET /api/vectordb/status
# 응답 예시:
{
    "status": "ok",
    "total_count": 408,
    "users": {
        "user@email.com": {
            "count": 30,
            "dates": ["2025-12-17", "2025-12-16", ...]
        }
    }
}
```

---

## 🗃️ VectorDB 데이터 구성

### Document ID 형식

```python
doc_id = f"{user_id}_{date}_{source}"
# 예: "user@email.com_2025-12-17_api_samsung"  (삼성 앱 API)
# 예: "user@email.com_2025-12-17_api_apple"     (애플 앱 API)
# 예: "user@email.com_2025-12-16_zip_samsung"  (삼성 ZIP)
# 예: "user@email.com_2025-12-15_zip_apple"    (애플 ZIP)
```

### Metadata 구조

```python
metadata = {
    # 식별 정보
    "user_id": "user@email.com",
    "date": "2025-12-17",              # YYYY-MM-DD
    "timestamp": 20251217,              # 정렬용 정수

    # 분석 결과
    "health_score": 75,                 # 건강 점수 (0-100)
    "recommended_intensity": "중",      # 권장 강도 (하/중/상)
    "fallback": False,                  # Fallback 사용 여부

    # 데이터 출처
    "source": "api_samsung",            # 데이터 출처
    "platform": "samsung",              # 플랫폼
    "updated_at": "20251217143000",     # 마지막 업데이트

    # 원본 데이터
    "summary_json": "{\"raw\": {...}, \"summary_text\": \"...\"}"
}
```

### source 종류

| source        | 설명                              |
| ------------- | --------------------------------- |
| `api_samsung` | 삼성 앱 API 전송 (Health Connect) |
| `api_apple`   | 애플 앱 API 전송 (HealthKit)      |
| `zip_samsung` | 삼성 ZIP 파일 업로드              |
| `zip_apple`   | 애플 ZIP 파일 업로드              |

### 중복 방지 메커니즘

```python
# vector_store.py
# 같은 날짜, 같은 출처는 덮어쓰기 (upsert)
doc_id = f"{user_id}_{date}_{source}"  # timestamp 제거!

collection.upsert(
    ids=[doc_id],
    embeddings=[embedding],
    documents=[embedding_text],
    metadatas=[metadata],
)
```

---

## 🚀 서버 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일)
OPENAI_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
ALLOWED_ORIGINS=http://localhost:3000

# 3. 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📡 API 엔드포인트 요약

| 엔드포인트                     | 메서드 | 설명                   |
| ------------------------------ | ------ | ---------------------- |
| `/api/file/upload`             | POST   | ZIP/DB 파일 업로드     |
| `/api/auto/upload`             | POST   | 앱 JSON 데이터 업로드  |
| `/api/user/latest-analysis`    | GET    | 최신 데이터 AI 분석    |
| `/api/user/raw-history`        | GET    | 사용자 전체 히스토리   |
| `/api/chat`                    | POST   | 자유형 챗봇            |
| `/api/chat/fixed`              | POST   | 고정형 챗봇            |
| `/api/similar`                 | POST   | 유사 패턴 검색         |
| `/api/vectordb/status`         | GET    | VectorDB 상태          |
| `/api/vectordb/user/{user_id}` | GET    | 사용자 VectorDB 데이터 |

# 헬스커넥트 앱(삼성) 파일

https://drive.google.com/file/d/1hi8NnbKfdOIvAicIdPqycBVbirFDkuN_/view?usp=drive_link

# 헬스킷 앱(애플) 파일

https://drive.google.com/file/d/12ZCi7mxL3ySzUSKyNsyc9vNOHv2GdWCB/view?usp=drive_link
